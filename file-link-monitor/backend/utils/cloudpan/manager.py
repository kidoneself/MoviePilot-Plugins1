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
    
    def __init__(self, headless: bool = False):
        """
        初始化
        
        Args:
            headless: 是否无头模式
        """
        self.headless = headless
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
            pan = pan_class(headless=self.headless)
            await pan.start()
            
            # 尝试登录
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
        expire_days: int = 0
    ) -> Dict[str, str]:
        """
        批量生成分享链接并更新到数据库
        
        Args:
            db: 数据库会话
            pan_type: 网盘类型（baidu/quark）
            target_path: 目标网盘路径前缀（如：/剧集/国产剧集）
            expire_days: 有效期天数
            
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
            
            # 根据网盘类型过滤
            if pan_type == 'baidu':
                # 只处理没有百度网盘链接的
                query = query.filter(
                    (CustomNameMapping.baidu_link == None) |
                    (CustomNameMapping.baidu_link == '')
                )
            elif pan_type == 'quark':
                # 只处理没有夸克网盘链接的
                query = query.filter(
                    (CustomNameMapping.quark_link == None) |
                    (CustomNameMapping.quark_link == '')
                )
            
            mappings = query.all()
            logger.info(f"📊 找到 {len(mappings)} 条需要生成{pan_type}链接的记录")
            
            results = {}
            
            # 批量处理
            for i, mapping in enumerate(mappings, 1):
                try:
                    logger.info(f"⏳ [{i}/{len(mappings)}] 处理: {mapping.custom_name}")
                    
                    # 构建完整路径
                    if target_path:
                        folder_path = f"{target_path}/{mapping.custom_name}"
                    else:
                        folder_path = mapping.custom_name
                    
                    # 创建分享链接
                    link = await pan.create_share_link(mapping.custom_name, expire_days)
                    
                    if link:
                        # 更新到数据库
                        if pan_type == 'baidu':
                            mapping.baidu_link = link
                        elif pan_type == 'quark':
                            mapping.quark_link = link
                        
                        db.commit()
                        results[mapping.original_name] = link
                        logger.info(f"✅ [{i}/{len(mappings)}] 成功: {mapping.custom_name} -> {link}")
                    else:
                        logger.warning(f"⚠️ [{i}/{len(mappings)}] 失败: {mapping.custom_name}")
                        results[mapping.original_name] = None
                    
                    # 避免频率限制
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ [{i}/{len(mappings)}] 错误: {mapping.custom_name} - {e}")
                    results[mapping.original_name] = None
            
            logger.info(f"🎉 批量生成完成！成功: {sum(1 for v in results.values() if v)}/{len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"批量生成链接失败: {e}")
            return {}
        finally:
            await self.close_all()
