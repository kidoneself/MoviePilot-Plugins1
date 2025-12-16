import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Notifier:
    """通知器：支持Server酱"""
    
    def __init__(self, config: dict):
        self.config = config
        self.notification_config = config.get('notification', {})
        self.enabled = self.notification_config.get('enabled', False)
        self.custom_url = self.notification_config.get('serverchan_url', '')
        self.sendkey = self.notification_config.get('serverchan_sendkey', '')
        
    def send_notification(self, title: str, content: str, tags: Optional[str] = None) -> bool:
        """发送通知
        
        Args:
            title: 通知标题
            content: 通知内容
            tags: 标签，如 "文件同步|成功"
        """
        if not self.enabled:
            logger.debug("通知未启用")
            return False
        
        # 优先使用自定义URL
        if self.custom_url:
            return self._send_with_custom_url(title, content, tags)
        elif self.sendkey:
            return self._send_with_sdk(title, content, tags)
        else:
            logger.debug("未配置Server酱URL或SendKey")
            return False
    
    def _send_with_custom_url(self, title: str, content: str, tags: Optional[str] = None) -> bool:
        """使用自定义URL发送通知"""
        try:
            import requests
            
            data = {
                "title": title,
                "desp": content
            }
            if tags:
                data["tags"] = tags
            
            response = requests.post(self.custom_url, data=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Server酱通知发送成功: {title}")
            return True
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False
    
    def _send_with_sdk(self, title: str, content: str, tags: Optional[str] = None) -> bool:
        """使用SDK发送通知"""
        try:
            from serverchan_sdk import sc_send
            
            options = {}
            if tags:
                options['tags'] = tags
            
            response = sc_send(self.sendkey, title, content, options)
            logger.info(f"Server酱通知发送成功: {title}")
            return True
        except ImportError:
            logger.error("serverchan-sdk未安装，请运行: pip install serverchan-sdk")
            return False
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False
    
    def notify_sync_success(self, file_name: str, target_files: list):
        """通知文件同步成功
        
        Args:
            file_name: 源文件名
            target_files: 目标描述列表，格式为 ["目标名称: 文件名", ...]
        """
        title = "📁 文件同步成功"
        target_list = "\n".join([f"- {desc}" for desc in target_files])
        content = f"""
**源文件**: `{file_name}`

**目标数量**: {len(target_files)}

**同步到**:
{target_list}
        """.strip()
        self.send_notification(title, content, "文件同步|成功")
    
    def notify_sync_failed(self, file_name: str, error: str):
        """通知文件同步失败"""
        title = "❌ 文件同步失败"
        content = f"""
**源文件**: `{file_name}`

**错误信息**: {error}
        """.strip()
        self.send_notification(title, content, "文件同步|失败")
    
    def notify_full_sync_complete(self, total: int, success: int, skipped: int, failed: int):
        """通知全量同步完成"""
        title = "🔄 全量同步完成"
        content = f"""
总文件数: {total}
新建链接: {success}
跳过文件: {skipped}
失败文件: {failed}
        """.strip()
        self.send_notification(title, content, "全量同步|完成")
    
    def notify_taosync_triggered(self, file_name: str):
        """通知TaoSync任务已触发"""
        title = "☁️ 云盘同步已触发"
        content = f"""
源文件: `{file_name}`

TaoSync同步任务已触发
正在同步到云盘...
        """.strip()
        self.send_notification(title, content, "TaoSync|触发")
    
    def notify_batch_sync_success(self, file_names: list):
        """通知批次同步成功"""
        title = "📁 批次同步完成"
        file_list = "\n".join([f"- {name}" for name in file_names])
        content = f"""
文件数量: {len(file_names)}

同步文件:
{file_list}

状态: 硬链接创建成功
        """.strip()
        self.send_notification(title, content, "批次同步|成功")
    
    def notify_taosync_triggered_batch(self, file_count: int):
        """通知批次TaoSync任务已触发"""
        title = "☁️ 云盘同步已触发"
        content = f"""
批次文件数: {file_count}

TaoSync同步任务已触发
正在同步到云盘...
        """.strip()
        self.send_notification(title, content, "TaoSync|批次触发")
