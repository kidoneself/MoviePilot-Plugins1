"""
网盘批量处理管理器
统一管理多个网盘的自动化操作
"""
import asyncio
import logging
from typing import Dict, List, Optional, Type
from sqlalchemy.orm import Session

from .base import CloudPanBase
from .baidu import BaiduPan
from .quark import QuarkPan

logger = logging.getLogger(__name__)


class CloudPanManager:
    """网盘批量处理管理器"""
    
    # 支持的网盘类型
    SUPPORTED_PANS = {
        'baidu': BaiduPan,
        'quark': QuarkPan,
    }
    
    def __init__(self, headless: bool = False, cookies_dir: str = "./cookies"):
        """
        初始化
        
        Args:
            headless: 是否无头模式
            cookies_dir: Cookie保存目录
        """
        self.headless = headless
        self.cookies_dir = cookies_dir
        self.pans: Dict[str, CloudPanBase] = {}
        
    async def init_pan(self, pan_type: str) -> Optional[CloudPanBase]:
        """
        初始化指定网盘
        
        Args:
            pan_type: 网盘类型（baidu/quark）
            
        Returns:
            网盘实例
        """
        if pan_type not in self.SUPPORTED_PANS:
            logger.error(f"不支持的网盘类型: {pan_type}")
            return None
        
        if pan_type in self.pans:
            return self.pans[pan_type]
        
        try:
            pan_class = self.SUPPORTED_PANS[pan_type]
            pan = pan_class(headless=self.headless, cookies_dir=self.cookies_dir)
            await pan.start()
            
            # 如果有cookie文件，跳过登录验证（cookie已在start时加载）
            # 直接开始使用，如果cookie无效会在操作时发现
            if pan.cookies_file.exists():
                logger.info(f"✅ 检测到{pan_type}网盘cookie，跳过登录验证")
                self.pans[pan_type] = pan
                return pan
            
            # 没有cookie，需要登录
            if not await pan.login(wait_for_scan=True):
                logger.error(f"{pan_type}网盘登录失败")
                await pan.close()
                return None
            
            self.pans[pan_type] = pan
            return pan
            
        except Exception as e:
            logger.error(f"初始化{pan_type}网盘失败: {e}")
            return None
    
    async def close_all(self):
        """关闭所有网盘"""
        for pan in self.pans.values():
            try:
                await pan.close()
            except Exception as e:
                logger.error(f"关闭网盘失败: {e}")
        self.pans.clear()
    
    async def batch_generate_links(
        self,
        db: Session,
        pan_type: str = 'baidu',
        target_path: str = None,
        expire_days: int = 0,
        original_name: str = None
    ) -> Dict[str, str]:
        """
        批量生成分享链接并更新到数据库
        
        Args:
            db: 数据库会话
            pan_type: 网盘类型（baidu/quark）
            target_path: 目标网盘路径前缀（如：/剧集/国产剧集）
            expire_days: 有效期天数
            original_name: 指定单个剧集名称（可选）
            
        Returns:
            {剧集名: 分享链接}
        """
        from backend.models import CustomNameMapping
        
        # 初始化网盘
        pan = await self.init_pan(pan_type)
        if not pan:
            return {}
        
        try:
            # 查询所有需要生成链接的映射
            query = db.query(CustomNameMapping).filter(
                CustomNameMapping.enabled == True
            )
            
            # 如果指定了剧集名，只处理该剧集
            if original_name:
                query = query.filter(CustomNameMapping.original_name == original_name)
            else:
                # 批量模式：根据网盘类型过滤没有链接的记录
                if pan_type == 'baidu':
                    query = query.filter(
                        (CustomNameMapping.baidu_link == None) |
                        (CustomNameMapping.baidu_link == '')
                    )
                elif pan_type == 'quark':
                    query = query.filter(
                        (CustomNameMapping.quark_link == None) |
                        (CustomNameMapping.quark_link == '')
                    )
            
            mappings = query.all()
            if original_name:
                logger.info(f"📊 找到指定剧集: {original_name}")
            else:
                logger.info(f"📊 找到 {len(mappings)} 条需要生成{pan_type}链接的记录")
            
            results = {}
            
            # 批量处理
            for i, mapping in enumerate(mappings, 1):
                try:
                    # 根据网盘类型使用对应的名称
                    folder_name = mapping.quark_name if pan_type == 'quark' else mapping.baidu_name
                    if not folder_name:
                        folder_name = mapping.original_name
                    
                    logger.info(f"⏳ [{i}/{len(mappings)}] 处理: {folder_name}")
                    
                    # 构建完整路径
                    if target_path:
                        folder_path = f"{target_path}/{folder_name}"
                    else:
                        folder_path = folder_name
                    
                    # 创建分享链接
                    link = await pan.create_share_link(folder_name, expire_days)
                    
                    if link:
                        # 更新到数据库
                        if pan_type == 'baidu':
                            mapping.baidu_link = link
                        elif pan_type == 'quark':
                            mapping.quark_link = link
                        
                        db.commit()
                        results[mapping.original_name] = link
                        logger.info(f"✅ [{i}/{len(mappings)}] 成功: {folder_name} -> {link}")
                    else:
                        logger.warning(f"⚠️ [{i}/{len(mappings)}] 失败: {folder_name}")
                        results[mapping.original_name] = None
                    
                    # 避免频率限制
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ [{i}/{len(mappings)}] 错误: {folder_name} - {e}")
                    results[mapping.original_name] = None
            
            # 统计成功数量
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"🎉 批量生成完成！成功: {success_count}/{len(results)}")
            logger.info("ℹ️  浏览器保持打开状态，请手动检查。完成后手动关闭浏览器窗口。")
            return results
            
        except Exception as e:
            logger.error(f"批量生成链接失败: {e}")
            logger.info("ℹ️  浏览器保持打开状态，请手动检查错误。")
            return {}
        # 不自动关闭浏览器，方便用户调试
