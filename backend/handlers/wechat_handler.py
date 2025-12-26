"""
企业微信指令处理器 - 处理用户命令并返回结果
"""
import logging
import re
from typing import Optional
from datetime import date
from backend.models import CustomNameMapping, LinkRecord, get_session
from backend.services.wechat_service import WeChatService

logger = logging.getLogger(__name__)


class WeChatCommandHandler:
    """企业微信指令处理器"""
    
    def __init__(self, wechat_service: WeChatService, db_engine):
        """
        初始化指令处理器
        
        Args:
            wechat_service: 企业微信服务实例
            db_engine: 数据库引擎
        """
        self.wechat = wechat_service
        self.db_engine = db_engine
        # 缓存用户搜索结果（key: user_id, value: list of mappings）
        self.user_search_cache = {}
    
    def handle_message(self, user_id: str, content: str):
        """
        处理用户消息
        
        Args:
            user_id: 用户ID
            content: 消息内容
        """
        content = content.strip()
        
        # 空消息
        if not content:
            return
        
        # 帮助指令
        if content in ['帮助', 'help', '?', '？']:
            self._send_help(user_id)
            return
        
        # 未完结剧集列表
        if content in ['未完结', '未完结剧集', 'unfinished']:
            self._handle_unfinished_shows(user_id)
            return
        
        # 立即检查TMDB更新
        if content in ['检查更新', '更新检查', 'check']:
            self._handle_check_updates(user_id)
            return
        
        # 数字选择（如果用户刚搜索过）
        if content.isdigit() and user_id in self.user_search_cache:
            self._handle_number_select(user_id, int(content))
            return
        
        # 默认：直接搜索剧名
        self._handle_search(user_id, content)
    
    def _send_help(self, user_id: str):
        """发送帮助信息"""
        help_text = """📖 剧集搜索助手

🔍 **使用方法**
直接发送剧名即可搜索
例：唐朝

📝 **多个结果时**
1️⃣ 系统返回编号列表
2️⃣ 回复数字查看对应剧集

📺 **TMDB功能**
- 「未完结」查看所有未完结剧集
- 「检查更新」立即检查剧集更新

💡 **提示**
- 支持模糊搜索
- 自动返回三网盘链接
- 发送「?」显示此帮助"""
        
        self.wechat.send_text(user_id, help_text)
    
    def _handle_search(self, user_id: str, keyword: str):
        """
        处理搜索指令
        
        Args:
            user_id: 用户ID
            keyword: 搜索关键词
        """
        session = get_session(self.db_engine)
        try:
            # 模糊搜索
            mappings = session.query(CustomNameMapping).filter(
                CustomNameMapping.original_name.like(f'%{keyword}%'),
                CustomNameMapping.enabled == True
            ).limit(10).all()
            
            if not mappings:
                self.wechat.send_text(
                    user_id,
                    f"😔 未找到相关剧集: {keyword}"
                )
                return
            
            # 只有一个结果，直接显示详情
            if len(mappings) == 1:
                self._send_mapping_detail(user_id, mappings[0])
            else:
                # 多个结果，显示编号列表，缓存结果
                self.user_search_cache[user_id] = mappings
                result_text = f"🔍 找到 {len(mappings)} 个结果:\n\n"
                for idx, m in enumerate(mappings, 1):
                    has_links = bool(m.quark_link or m.baidu_link or m.xunlei_link)
                    status = "✅" if has_links else "⏳"
                    result_text += f"{status} {idx}. {m.original_name}\n"
                
                result_text += f"\n💡 回复数字查看对应剧集链接"
                self.wechat.send_text(user_id, result_text)
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            self.wechat.send_text(user_id, f"❌ 搜索失败: {str(e)}")
        finally:
            session.close()
    
    def _send_mapping_detail(self, user_id: str, mapping: CustomNameMapping):
        """发送剧集详情"""
        # 分享链接
        if not (mapping.quark_link or mapping.baidu_link or mapping.xunlei_link):
            self.wechat.send_text(user_id, f"😔 {mapping.original_name}\n\n暂无分享链接")
            return
        
        # 生成短链接
        from backend.services.wechat_service import WeChatService
        short_url = f"https://link.frp.naspt.vip/s/{mapping.id}"
        
        # 状态
        status = "✅ 完结" if mapping.is_completed else "📺 更新中"
        
        # 发送简洁消息
        message = f"""📺 {mapping.original_name}

{status}

🔗 点击查看三网盘链接：
{short_url}"""
        
        self.wechat.send_text(user_id, message)
    
    def _handle_number_select(self, user_id: str, num: int):
        """处理数字选择"""
        mappings = self.user_search_cache.get(user_id, [])
        
        if not mappings:
            self.wechat.send_text(user_id, "❌ 没有可选择的搜索结果")
            return
        
        if num < 1 or num > len(mappings):
            self.wechat.send_text(
                user_id,
                f"❌ 请输入 1-{len(mappings)} 之间的数字"
            )
            return
        
        # 发送选中的剧集详情
        selected = mappings[num - 1]
        self._send_mapping_detail(user_id, selected)
    
    def _handle_today_update(self, user_id: str):
        """处理今日更新查询"""
        session = get_session(self.db_engine)
        try:
            today = date.today()
            records = session.query(LinkRecord).filter(
                LinkRecord.created_at >= today
            ).order_by(LinkRecord.created_at.desc()).all()
            
            if not records:
                self.wechat.send_text(user_id, "📭 今天还没有更新")
                return
            
            # 按原名分组统计
            show_stats = {}
            for record in records:
                show_name = record.original_name
                if show_name not in show_stats:
                    show_stats[show_name] = 0
                show_stats[show_name] += 1
            
            # 构建消息
            content = f"📅 今日更新 ({len(records)}个文件)\n\n"
            for idx, (show, count) in enumerate(show_stats.items(), 1):
                content += f"{idx}. {show} ({count}集)\n"
            
            content += f"\n💡 发送「搜索 剧名」查看链接"
            
            self.wechat.send_text(user_id, content)
            
        except Exception as e:
            logger.error(f"查询今日更新失败: {e}")
            self.wechat.send_text(user_id, f"❌ 查询失败: {str(e)}")
        finally:
            session.close()
    
    def _handle_generate_link(self, user_id: str, name: str):
        """处理生成链接指令"""
        self.wechat.send_text(
            user_id,
            f"⏳ 正在为「{name}」生成分享链接...\n\n此功能开发中，请稍后"
        )
    
    def _handle_pansou(self, user_id: str, keyword: str):
        """处理盘搜指令"""
        self.wechat.send_text(
            user_id,
            f"🔍 正在搜索「{keyword}」...\n\n此功能开发中，请稍后"
        )
    
    def _handle_unfinished_shows(self, user_id: str):
        """处理未完结剧集查询指令"""
        session = get_session(self.db_engine)
        try:
            from datetime import datetime
            
            # 查询所有未完结的电视剧
            tv_shows = session.query(CustomNameMapping).filter(
                CustomNameMapping.media_type == 'tv',
                CustomNameMapping.is_completed == False,
                CustomNameMapping.tmdb_id.isnot(None)
            ).all()
            
            # 构建消息
            now = datetime.now()
            content_parts = [f"📺 未完结剧集汇总 ({now.strftime('%H:%M')})\n"]
            
            if not tv_shows:
                content_parts.append("✅ 当前没有未完结的剧集")
            else:
                content_parts.append(f"共有 {len(tv_shows)} 部未完结剧集：\n")
                
                # 按名称排序
                sorted_shows = sorted(tv_shows, key=lambda x: x.original_name)
                
                for i, show in enumerate(sorted_shows, 1):
                    content_parts.append(f"{i}. {show.original_name}")
                    
                    # 如果有分享链接，添加短链接
                    if hasattr(show, 'id'):
                        short_url = f"https://link.frp.naspt.vip/s/{show.id}"
                        content_parts.append(f"   🔗 {short_url}")
            
            content_parts.append(f"\n⏰ 查询时间: {now.strftime('%Y-%m-%d %H:%M')}")
            
            message = "\n".join(content_parts)
            self.wechat.send_text(user_id, message)
            logger.info(f"✅ 已发送未完结剧集列表给用户 {user_id} (共{len(tv_shows)}部)")
            
        except Exception as e:
            logger.error(f"查询未完结剧集失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 查询失败: {str(e)}")
        finally:
            session.close()
    
    def _handle_check_updates(self, user_id: str):
        """处理立即检查更新指令"""
        import asyncio
        
        try:
            # 先发送确认消息
            self.wechat.send_text(user_id, "⏳ 正在检查TMDB剧集更新...\n\n这可能需要几分钟，请稍后")
            
            # 异步执行检查
            async def do_check():
                try:
                    from backend.services.tmdb_scheduler import get_checker
                    checker = get_checker()
                    if checker and checker.running:
                        await checker._check_tv_updates()
                        logger.info(f"✅ 用户 {user_id} 触发的更新检查已完成")
                    else:
                        self.wechat.send_text(user_id, "❌ TMDB检查器未运行")
                except Exception as e:
                    logger.error(f"检查更新失败: {e}", exc_info=True)
                    self.wechat.send_text(user_id, f"❌ 检查失败: {str(e)}")
            
            # 在后台执行
            asyncio.create_task(do_check())
            
        except Exception as e:
            logger.error(f"触发更新检查失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 触发失败: {str(e)}")
