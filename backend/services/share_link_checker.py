"""
分享链接检查调度器
定期检查没有分享链接的资源并发送通知
"""
import logging
import asyncio
from datetime import datetime, time
from typing import Optional, List, Dict
from sqlalchemy import or_

from backend.models import get_session, CustomNameMapping

logger = logging.getLogger(__name__)


def _get_session():
    """获取数据库会话"""
    from backend.main import db_engine
    return get_session(db_engine)


class ShareLinkChecker:
    """分享链接检查器"""
    
    def __init__(self, wechat_service=None, check_interval_hours: int = 24):
        """
        初始化检查器
        
        Args:
            wechat_service: 企业微信服务实例
            check_interval_hours: 检查间隔（小时）
        """
        self.running = False
        self.wechat_service = wechat_service
        self.check_interval_hours = check_interval_hours
        self.check_times = []  # 每天的检查时间点，例如 [9, 15, 21] 表示9点、15点、21点
        
        # 根据间隔计算检查时间点
        if check_interval_hours == 24:
            self.check_times = [9]  # 每天9点检查一次
        elif check_interval_hours == 12:
            self.check_times = [9, 21]  # 每天9点和21点
        elif check_interval_hours == 8:
            self.check_times = [9, 17, 1]  # 每天9点、17点、凌晨1点
        elif check_interval_hours == 6:
            self.check_times = [9, 15, 21, 3]  # 每6小时
        elif check_interval_hours == 4:
            self.check_times = [9, 13, 17, 21, 1, 5]  # 每4小时
        else:
            self.check_times = [9]  # 默认每天9点
    
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("分享链接检查器已在运行")
            return
        
        self.running = True
        logger.info(f"🔗 分享链接检查器启动 (检查间隔: {self.check_interval_hours}小时)")
        
        # 启动定时检查循环
        asyncio.create_task(self._check_loop())
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("分享链接检查器已停止")
    
    async def _check_loop(self):
        """定时检查循环"""
        while self.running:
            try:
                now = datetime.now()
                current_hour = now.hour
                
                # 检查是否到了执行时间
                if current_hour in self.check_times and now.minute == 0:
                    logger.info("⏰ 开始检查缺失的分享链接")
                    await self.check_missing_links()
                    
                    # 等待61秒，避免重复执行
                    await asyncio.sleep(61)
                else:
                    # 每分钟检查一次时间
                    await asyncio.sleep(60)
                    
            except Exception as e:
                logger.error(f"检查任务失败: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def check_missing_links(self, send_notification: bool = True) -> Dict:
        """
        检查缺失的分享链接
        
        Args:
            send_notification: 是否发送通知
            
        Returns:
            检查结果字典
        """
        session = _get_session()
        try:
            # 1. 查询所有启用的映射
            all_mappings = session.query(CustomNameMapping).filter(
                CustomNameMapping.enabled == True
            ).all()
            
            # 2. 统计缺失链接的资源
            missing_links = {
                'baidu': [],
                'quark': [],
                'xunlei': [],
                'all_missing': []  # 三个网盘都没有链接
            }
            
            for mapping in all_mappings:
                has_baidu = bool(mapping.baidu_link and mapping.baidu_link.strip())
                has_quark = bool(mapping.quark_link and mapping.quark_link.strip())
                has_xunlei = bool(mapping.xunlei_link and mapping.xunlei_link.strip())
                
                # 分别统计各网盘缺失的
                if not has_baidu:
                    missing_links['baidu'].append({
                        'id': mapping.id,
                        'name': mapping.original_name,
                        'category': mapping.category or '未分类',
                        'completed': mapping.is_completed or False
                    })
                
                if not has_quark:
                    missing_links['quark'].append({
                        'id': mapping.id,
                        'name': mapping.original_name,
                        'category': mapping.category or '未分类',
                        'completed': mapping.is_completed or False
                    })
                
                if not has_xunlei:
                    missing_links['xunlei'].append({
                        'id': mapping.id,
                        'name': mapping.original_name,
                        'category': mapping.category or '未分类',
                        'completed': mapping.is_completed or False
                    })
                
                # 三个都没有的
                if not has_baidu and not has_quark and not has_xunlei:
                    missing_links['all_missing'].append({
                        'id': mapping.id,
                        'name': mapping.original_name,
                        'category': mapping.category or '未分类',
                        'completed': mapping.is_completed or False
                    })
            
            # 3. 统计结果
            result = {
                'success': True,
                'check_time': datetime.now().isoformat(),
                'total_mappings': len(all_mappings),
                'missing_counts': {
                    'baidu': len(missing_links['baidu']),
                    'quark': len(missing_links['quark']),
                    'xunlei': len(missing_links['xunlei']),
                    'all_missing': len(missing_links['all_missing'])
                },
                'missing_links': missing_links
            }
            
            logger.info(
                f"✅ 检查完成: 总计{len(all_mappings)}个资源, "
                f"缺失百度{len(missing_links['baidu'])}个, "
                f"缺失夸克{len(missing_links['quark'])}个, "
                f"缺失迅雷{len(missing_links['xunlei'])}个, "
                f"全部缺失{len(missing_links['all_missing'])}个"
            )
            
            # 4. 发送通知
            if send_notification:
                await self._send_notification(result)
            
            return result
            
        except Exception as e:
            logger.error(f"检查缺失链接失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'check_time': datetime.now().isoformat()
            }
        finally:
            session.close()
    
    async def _send_notification(self, result: Dict):
        """发送微信通知"""
        if not self.wechat_service:
            logger.warning("微信服务未配置，跳过通知")
            return
        
        try:
            missing_counts = result['missing_counts']
            missing_links = result['missing_links']
            total = result['total_mappings']
            
            # 构建通知内容
            content_parts = ["🔗 分享链接检查报告\n"]
            content_parts.append(f"📊 资源总数: {total}个\n")
            
            # 统计缺失情况
            content_parts.append("📉 缺失链接统计:")
            content_parts.append(f"  百度网盘: {missing_counts['baidu']}个")
            content_parts.append(f"  夸克网盘: {missing_counts['quark']}个")
            content_parts.append(f"  迅雷网盘: {missing_counts['xunlei']}个")
            content_parts.append(f"  全部缺失: {missing_counts['all_missing']}个\n")
            
            # 显示全部缺失的资源列表
            if missing_links['all_missing']:
                content_parts.append("⚠️ 以下资源尚未生成任何分享链接:")
                
                # 按分类分组
                by_category = {}
                for item in missing_links['all_missing']:
                    category = item['category']
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(item)
                
                # 最多显示前20个
                shown_count = 0
                max_show = 20
                
                for category in sorted(by_category.keys()):
                    if shown_count >= max_show:
                        break
                    
                    items = by_category[category]
                    content_parts.append(f"\n【{category}】")
                    
                    for item in items[:5]:  # 每个分类最多5个
                        if shown_count >= max_show:
                            break
                        
                        completed_tag = "✅" if item['completed'] else "🔄"
                        content_parts.append(f"{completed_tag} {item['name']}")
                        shown_count += 1
                    
                    if len(items) > 5:
                        content_parts.append(f"  ... 还有{len(items) - 5}个")
                
                if len(missing_links['all_missing']) > max_show:
                    content_parts.append(f"\n... 还有{len(missing_links['all_missing']) - max_show}个")
            else:
                content_parts.append("✅ 所有资源都已生成分享链接")
            
            content_parts.append(f"\n⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            content_parts.append("\n💡 提示: 可通过API手动生成缺失的链接")
            
            message = "\n".join(content_parts)
            
            # 从配置获取用户ID
            from backend.main import app_config
            wechat_config = app_config.get('wechat', {})
            default_user = wechat_config.get('default_user', '@all')
            
            # 发送通知
            self.wechat_service.send_text(default_user, message)
            logger.info("✅ 已发送微信通知")
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}", exc_info=True)
    
    async def get_missing_links_by_category(self, pan_type: str = 'all') -> Dict:
        """
        按分类获取缺失链接的资源
        
        Args:
            pan_type: 网盘类型 (baidu/quark/xunlei/all)
            
        Returns:
            按分类分组的缺失链接列表
        """
        session = _get_session()
        try:
            # 构建查询条件
            if pan_type == 'baidu':
                query = session.query(CustomNameMapping).filter(
                    CustomNameMapping.enabled == True,
                    or_(
                        CustomNameMapping.baidu_link == None,
                        CustomNameMapping.baidu_link == ''
                    )
                )
            elif pan_type == 'quark':
                query = session.query(CustomNameMapping).filter(
                    CustomNameMapping.enabled == True,
                    or_(
                        CustomNameMapping.quark_link == None,
                        CustomNameMapping.quark_link == ''
                    )
                )
            elif pan_type == 'xunlei':
                query = session.query(CustomNameMapping).filter(
                    CustomNameMapping.enabled == True,
                    or_(
                        CustomNameMapping.xunlei_link == None,
                        CustomNameMapping.xunlei_link == ''
                    )
                )
            else:  # all - 三个都没有
                query = session.query(CustomNameMapping).filter(
                    CustomNameMapping.enabled == True,
                    or_(
                        CustomNameMapping.baidu_link == None,
                        CustomNameMapping.baidu_link == ''
                    ),
                    or_(
                        CustomNameMapping.quark_link == None,
                        CustomNameMapping.quark_link == ''
                    ),
                    or_(
                        CustomNameMapping.xunlei_link == None,
                        CustomNameMapping.xunlei_link == ''
                    )
                )
            
            mappings = query.all()
            
            # 按分类分组
            by_category = {}
            for mapping in mappings:
                category = mapping.category or '未分类'
                if category not in by_category:
                    by_category[category] = []
                
                by_category[category].append({
                    'id': mapping.id,
                    'original_name': mapping.original_name,
                    'category': category,
                    'is_completed': mapping.is_completed or False,
                    'baidu_name': mapping.baidu_name,
                    'quark_name': mapping.quark_name,
                    'xunlei_name': mapping.xunlei_name,
                    'has_baidu_link': bool(mapping.baidu_link and mapping.baidu_link.strip()),
                    'has_quark_link': bool(mapping.quark_link and mapping.quark_link.strip()),
                    'has_xunlei_link': bool(mapping.xunlei_link and mapping.xunlei_link.strip())
                })
            
            return {
                'success': True,
                'pan_type': pan_type,
                'total_count': len(mappings),
                'categories': by_category,
                'check_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取缺失链接失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()


# 全局检查器实例
_checker_instance: Optional[ShareLinkChecker] = None


def get_checker() -> Optional[ShareLinkChecker]:
    """获取检查器实例"""
    return _checker_instance


def init_checker(wechat_service=None, check_interval_hours: int = 24) -> ShareLinkChecker:
    """
    初始化检查器
    
    Args:
        wechat_service: 企业微信服务实例
        check_interval_hours: 检查间隔（小时）
    """
    global _checker_instance
    _checker_instance = ShareLinkChecker(wechat_service, check_interval_hours)
    return _checker_instance

