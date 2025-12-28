"""
夸克转存处理器 - 集成到企业微信
处理用户发送分享链接的完整转存流程
"""
import logging
import re
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# API配置
API_BASE = "http://127.0.0.1:9889/api"  # 本地API地址


class QuarkTransferHandler:
    """夸克转存处理器"""
    
    def __init__(self, wechat_service):
        """
        初始化转存处理器
        
        Args:
            wechat_service: 企业微信服务实例
        """
        self.wechat = wechat_service
        # 用户会话缓存（key: user_id, value: session_data）
        self.user_sessions = {}
    
    def can_handle(self, content: str) -> bool:
        """
        判断是否是夸克分享链接
        
        Args:
            content: 用户消息内容
            
        Returns:
            是否可以处理
        """
        return 'pan.quark.cn/s/' in content
    
    def handle(self, user_id: str, content: str):
        """
        处理用户消息（状态机）
        
        Args:
            user_id: 用户ID
            content: 消息内容
        """
        content = content.strip()
        
        # 获取用户会话
        session = self.user_sessions.get(user_id)
        
        # 如果是新链接，开始新流程
        if 'pan.quark.cn/s/' in content:
            self._start_new_transfer(user_id, content)
            return
        
        # 如果没有会话，忽略
        if not session:
            return
        
        # 根据状态处理
        state = session.get('state')
        
        if state == 'waiting_file_selection':
            self._handle_file_selection(user_id, content)
        elif state == 'waiting_media_name':
            self._handle_media_name(user_id, content)
        elif state == 'waiting_confirm':
            self._handle_confirm(user_id, content)
        else:
            logger.warning(f"未知状态: {state}")
    
    def _start_new_transfer(self, user_id: str, content: str):
        """开始新的转存流程"""
        # 提取链接
        match = re.search(r'https://pan\.quark\.cn/s/[^\s]+', content)
        if not match:
            self.wechat.send_text(user_id, "❌ 无法识别夸克分享链接")
            return
        
        share_url = match.group(0)
        
        # 调用API解析链接
        self.wechat.send_text(user_id, "⏳ 正在解析链接...")
        
        try:
            resp = requests.post(f"{API_BASE}/quark/parse-share", json={
                "share_url": share_url
            }, timeout=30)
            
            data = resp.json()
            
            if not data.get('success'):
                self.wechat.send_text(user_id, f"❌ 解析失败: {data.get('message', '未知错误')}")
                return
            
            # 保存会话
            self.user_sessions[user_id] = {
                'state': 'waiting_file_selection',
                'session_id': data['session_id'],
                'share_url': share_url,
                'files': data['files'],
                'stats': data['stats']
            }
            
            # 构建文件列表消息
            stats = data['stats']
            files = data['files']
            
            message_parts = [
                f"📦 文件列表（共{stats['total']}个）\n",
                f"✅ 干净文件：{stats['clean_count']}个",
                f"🚫 广告文件：{stats['ad_count']}个\n"
            ]
            
            # 显示前10个干净文件
            clean_files = [f for f in files if not f['is_ad']]
            for i, file in enumerate(clean_files[:10], 1):
                size_mb = file['size'] / 1024 / 1024
                message_parts.append(f"{i}. {file['name']} ({size_mb:.1f}MB)")
            
            if len(clean_files) > 10:
                message_parts.append(f"... 还有 {len(clean_files) - 10} 个文件")
            
            message_parts.extend([
                "\n━━━━━━━━━━━━━━━",
                "请回复：",
                "• all - 全选干净文件",
                "• 1,3,5 - 选择指定序号",
                "• 1-10 - 选择范围"
            ])
            
            self.wechat.send_text(user_id, "\n".join(message_parts))
            
        except requests.Timeout:
            self.wechat.send_text(user_id, "❌ 请求超时，请稍后重试")
        except Exception as e:
            logger.error(f"解析链接失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 解析失败: {str(e)}")
    
    def _handle_file_selection(self, user_id: str, content: str):
        """处理文件选择"""
        session = self.user_sessions[user_id]
        
        try:
            resp = requests.post(f"{API_BASE}/quark/select-files", json={
                "session_id": session['session_id'],
                "selection": content
            }, timeout=10)
            
            data = resp.json()
            
            if not data.get('success'):
                self.wechat.send_text(user_id, f"❌ {data.get('message', '选择失败')}")
                return
            
            # 更新状态
            session['state'] = 'waiting_media_name'
            session['selected_count'] = data['selected_count']
            
            message = f"✅ 已选择 {data['selected_count']} 个文件\n\n🎬 请输入剧名（如：老舅）"
            
            if data.get('skipped_ads'):
                message += f"\n\n⚠️ 已自动跳过 {len(data['skipped_ads'])} 个广告文件"
            
            self.wechat.send_text(user_id, message)
            
        except Exception as e:
            logger.error(f"选择文件失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 操作失败: {str(e)}")
    
    def _handle_media_name(self, user_id: str, content: str):
        """处理剧名输入"""
        session = self.user_sessions[user_id]
        media_name = content.strip()
        
        try:
            resp = requests.post(f"{API_BASE}/quark/get-target-path", json={
                "session_id": session['session_id'],
                "media_name": media_name
            }, timeout=10)
            
            data = resp.json()
            
            if not data.get('success'):
                error_msg = data.get('message', '未找到映射')
                self.wechat.send_text(user_id, f"❌ {error_msg}\n\n💡 请重新输入剧名，或发送新链接重新开始")
                return
            
            # 更新状态
            session['state'] = 'waiting_confirm'
            session['media_name'] = media_name
            session['target_path'] = data['display_path']
            
            message = f"""✅ 找到保存位置
            
📂 {data['display_path']}

━━━━━━━━━━━━━━━
📋 转存信息：
• 剧名：{data['media_name']}
• 文件：{session['selected_count']}个
• 位置：{data['display_path']}

━━━━━━━━━━━━━━━
确认转存请回复：确认
取消请回复：取消"""
            
            self.wechat.send_text(user_id, message)
            
        except Exception as e:
            logger.error(f"查询路径失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 操作失败: {str(e)}")
    
    def _handle_confirm(self, user_id: str, content: str):
        """处理确认转存"""
        session = self.user_sessions[user_id]
        
        if content not in ['确认', '确定', 'ok', 'yes', 'y']:
            self.wechat.send_text(user_id, "❌ 已取消转存")
            # 清除会话
            del self.user_sessions[user_id]
            return
        
        try:
            # 执行转存
            self.wechat.send_text(user_id, "⏳ 正在转存，请稍候...")
            
            resp = requests.post(f"{API_BASE}/quark/execute-transfer", json={
                "session_id": session['session_id']
            }, timeout=10)
            
            data = resp.json()
            
            if not data.get('success'):
                self.wechat.send_text(user_id, f"❌ 转存失败: {data.get('message', '未知错误')}")
                return
            
            task_id = data['task_id']
            mode = data['mode']
            
            # 轮询任务状态
            import time
            max_retries = 30
            
            for i in range(max_retries):
                time.sleep(2)  # 每2秒查询一次
                
                try:
                    status_resp = requests.get(f"{API_BASE}/quark/task-status/{task_id}", timeout=10)
                    status_data = status_resp.json()
                    
                    if status_data.get('status') == 'completed':
                        # 转存完成
                        message = f"""✅ 转存完成！

• 已保存：{status_data['transferred']}个文件
• 已过滤：{status_data['ad_filtered']}个广告
• 保存位置：{status_data['display_path']}
• 转存策略：{status_data['mode']}"""
                        
                        self.wechat.send_text(user_id, message)
                        
                        # 清除会话
                        del self.user_sessions[user_id]
                        return
                    
                except Exception as e:
                    logger.warning(f"查询任务状态失败: {e}")
                    continue
            
            # 超时
            self.wechat.send_text(user_id, "⚠️ 转存任务仍在进行中，请稍后在网盘中查看")
            del self.user_sessions[user_id]
            
        except Exception as e:
            logger.error(f"执行转存失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 操作失败: {str(e)}")
            # 清除会话
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

