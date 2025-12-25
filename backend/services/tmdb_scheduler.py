"""
TMDB剧集更新检查调度器
每天检查未完结剧集是否有更新
"""
import logging
import asyncio
from datetime import datetime, time
from typing import Optional
import requests

from backend.models import get_session, CustomNameMapping

logger = logging.getLogger(__name__)

# TMDb API 配置
TMDB_API_KEY = "c7f3349aa08d38fe2e391ec5a4c0279c"
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def _get_session():
    """获取数据库会话"""
    from backend.main import db_engine
    return get_session(db_engine)


class TmdbUpdateChecker:
    """TMDB剧集更新检查器"""
    
    def __init__(self, wechat_service=None):
        self.running = False
        self.wechat_service = wechat_service
    
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("TMDB调度器已在运行")
            return
        
        self.running = True
        logger.info("🎬 TMDB剧集更新检查器启动")
        
        # 启动定时检查循环
        asyncio.create_task(self._check_loop())
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("TMDB剧集更新检查器已停止")
    
    async def _check_loop(self):
        """定时检查循环 - 每天早上9点检查"""
        while self.running:
            try:
                now = datetime.now()
                
                # 检查是否到了执行时间（每天9:00）
                target_time = time(9, 0)
                
                if now.time().hour == target_time.hour and now.time().minute == target_time.minute:
                    logger.info("⏰ 开始检查TMDB剧集更新")
                    await self._check_tv_updates()
                    
                    # 等待61秒，避免重复执行
                    await asyncio.sleep(61)
                else:
                    # 每分钟检查一次时间
                    await asyncio.sleep(60)
                    
            except Exception as e:
                logger.error(f"检查任务失败: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _check_tv_updates(self):
        """检查所有未完结剧集的更新"""
        session = _get_session()
        try:
            # 查询所有未完结的电视剧
            tv_shows = session.query(CustomNameMapping).filter(
                CustomNameMapping.media_type == 'tv',
                CustomNameMapping.is_completed == False,
                CustomNameMapping.tmdb_id.isnot(None)
            ).all()
            
            if not tv_shows:
                logger.info("📺 没有需要检查的未完结剧集")
                return
            
            logger.info(f"📺 开始检查 {len(tv_shows)} 部未完结剧集")
            
            updates = []
            completed_shows = []
            
            for show in tv_shows:
                try:
                    update_info = await self._check_single_show(show, session)
                    if update_info:
                        if update_info['type'] == 'completed':
                            completed_shows.append(update_info)
                        else:
                            updates.append(update_info)
                    
                    # 避免请求过快
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"检查剧集 {show.original_name} 失败: {e}")
            
            # 发送通知
            if updates or completed_shows:
                await self._send_notification(updates, completed_shows)
            else:
                logger.info("✅ 所有剧集无更新")
        
        finally:
            session.close()
    
    async def _check_single_show(self, show: CustomNameMapping, session) -> Optional[dict]:
        """检查单个剧集的更新状态"""
        try:
            url = f"{TMDB_BASE_URL}/tv/{show.tmdb_id}"
            params = {
                "api_key": TMDB_API_KEY,
                "language": "zh-CN"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if not response.ok:
                logger.warning(f"获取 {show.original_name} 信息失败: {response.status_code}")
                return None
            
            data = response.json()
            
            # 检查剧集状态
            status = data.get('status', '')
            number_of_seasons = data.get('number_of_seasons', 0)
            number_of_episodes = data.get('number_of_episodes', 0)
            
            # 检查是否完结
            if status in ['Ended', 'Canceled']:
                # 更新数据库
                show.is_completed = True
                session.commit()
                logger.info(f"✅ {show.original_name} 已完结")
                
                return {
                    'type': 'completed',
                    'title': show.original_name,
                    'status': status,
                    'seasons': number_of_seasons,
                    'episodes': number_of_episodes
                }
            
            # 这里可以添加更复杂的更新检测逻辑
            # 比如保存上次检查的季数/集数，对比是否有新增
            # 现在简化处理，只检测完结状态
            
            return None
            
        except Exception as e:
            logger.error(f"检查 {show.original_name} 异常: {e}")
            return None
    
    async def _send_notification(self, updates: list, completed_shows: list):
        """发送微信通知"""
        if not self.wechat_service:
            logger.warning("微信服务未配置，跳过通知")
            return
        
        try:
            # 构建通知内容
            content_parts = ["📺 TMDB剧集更新提醒\n"]
            
            if completed_shows:
                content_parts.append("🎉 以下剧集已完结：")
                for show in completed_shows:
                    status_text = "已完结" if show['status'] == 'Ended' else "已取消"
                    content_parts.append(
                        f"• {show['title']}\n"
                        f"  状态：{status_text}\n"
                        f"  共{show['seasons']}季 {show['episodes']}集"
                    )
                content_parts.append("")
            
            if updates:
                content_parts.append("🔔 以下剧集有更新：")
                for update in updates:
                    content_parts.append(f"• {update['title']}")
                content_parts.append("")
            
            content_parts.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
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


# 全局调度器实例
_checker_instance: Optional[TmdbUpdateChecker] = None


def get_checker() -> TmdbUpdateChecker:
    """获取检查器实例"""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = TmdbUpdateChecker()
    return _checker_instance


def init_checker(wechat_service):
    """初始化检查器（带微信服务）"""
    global _checker_instance
    _checker_instance = TmdbUpdateChecker(wechat_service)
    return _checker_instance

