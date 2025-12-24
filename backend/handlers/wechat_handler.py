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
        
        # 默认：直接搜索剧名
        self._handle_search(user_id, content)
    
    def _send_help(self, user_id: str):
        """发送帮助信息"""
        help_text = """📖 剧集搜索助手

🔍 **使用方法**
直接发送剧名即可搜索
例：唐朝诡事录

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
                return
            
            # 多个结果，显示列表
            result_text = f"🔍 找到 {len(mappings)} 个结果:\n\n"
            for idx, m in enumerate(mappings, 1):
                has_links = bool(m.quark_link or m.baidu_link or m.xunlei_link)
                status = "✅" if has_links else "⏳"
                result_text += f"{status} {idx}. {m.original_name}\n"
            
            result_text += f"\n💡 发送「搜索 完整剧名」查看详情"
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
        
        # 构建简洁的文本消息（直接使用数据库存储的完整链接）
        lines = [f"📺 {mapping.original_name}\n\n"]
        
        if mapping.quark_link:
            lines.append(f"🟡 夸克:\n{mapping.quark_link}\n\n")
        
        if mapping.baidu_link:
            lines.append(f"🔵 百度:\n{mapping.baidu_link}\n\n")
        
        if mapping.xunlei_link:
            lines.append(f"🔴 迅雷:\n{mapping.xunlei_link}\n\n")
        
        # 状态
        status = "✅ 完结" if mapping.is_completed else "📺 更新中"
        lines.append(status)
        
        self.wechat.send_text(user_id, "".join(lines))
    
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
