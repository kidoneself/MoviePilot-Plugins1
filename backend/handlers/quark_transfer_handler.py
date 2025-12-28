"""
夸克转存处理器 - 集成到企业微信
处理用户发送分享链接的完整转存流程
"""
import logging
import re
import asyncio
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class QuarkTransferHandler:
    """夸克转存处理器"""
    
    def __init__(self, wechat_service, db_engine):
        """
        初始化转存处理器
        
        Args:
            wechat_service: 企业微信服务实例
            db_engine: 数据库引擎
        """
        self.wechat = wechat_service
        self.db_engine = db_engine
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
            # 直接导入并调用API函数
            from backend.api.quark_smart_transfer import (
                parse_share_url, get_cookie_from_db, get_quark_stoken, 
                get_quark_file_list, is_ad_file, sessions
            )
            import uuid
            from datetime import datetime
            
            # 解析URL
            pwd_id, pdir_fid = parse_share_url(share_url)
            
            # 获取Cookie
            cookie = get_cookie_from_db()
            
            # 获取stoken
            stoken = get_quark_stoken(cookie, pwd_id)
            
            # 获取文件列表
            share_info = get_quark_file_list(cookie, pwd_id, stoken, pdir_fid)
            
            # 处理文件列表
            files = []
            ad_count = 0
            clean_count = 0
            
            for idx, file in enumerate(share_info['files'], 1):
                is_ad = is_ad_file(file['file_name'], file['size'])
                
                files.append({
                    'index': idx,
                    'fid': file['fid'],
                    'name': file['file_name'],
                    'size': file['size'],
                    'is_ad': is_ad,
                    'share_fid_token': file['share_fid_token']
                })
                
                if is_ad:
                    ad_count += 1
                else:
                    clean_count += 1
            
            # 创建会话
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'created_at': datetime.now(),
                'share_url': share_url,
                'pwd_id': pwd_id,
                'pdir_fid': pdir_fid,
                'stoken': stoken,
                'cookie': cookie,
                'files': files,
                'selected_files': None,
                'media_name': None,
                'target_path': None,
                'target_fid': None
            }
            
            # 保存到本地会话
            self.user_sessions[user_id] = {
                'state': 'waiting_file_selection',
                'session_id': session_id,
                'share_url': share_url,
                'files': files,
                'stats': {
                    'total': len(files),
                    'ad_count': ad_count,
                    'clean_count': clean_count
                }
            }
            
            # 构建文件列表消息
            stats = self.user_sessions[user_id]['stats']
            
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
            
            logger.info(f"✅ 用户 {user_id} 解析成功，会话ID: {session_id}")
            
        except Exception as e:
            logger.error(f"解析链接失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 解析失败: {str(e)}")
    
    def _handle_file_selection(self, user_id: str, content: str):
        """处理文件选择"""
        session_data = self.user_sessions[user_id]
        
        try:
            # 直接调用API函数
            from backend.api.quark_smart_transfer import sessions, parse_file_selection
            
            session_id = session_data['session_id']
            session = sessions.get(session_id)
            
            if not session:
                self.wechat.send_text(user_id, "❌ 会话已过期，请重新发送链接")
                del self.user_sessions[user_id]
                return
            
            # 解析选择
            total_files = len(session['files'])
            selected_indices = parse_file_selection(content, total_files)
            
            # 过滤文件（排除广告）
            selected_files = []
            skipped_ads = []
            
            for idx in selected_indices:
                if 1 <= idx <= total_files:
                    file = session['files'][idx - 1]
                    
                    if file['is_ad']:
                        skipped_ads.append(file['name'])
                    else:
                        selected_files.append(file)
            
            # 保存选择
            session['selected_files'] = selected_files
            session_data['selected_count'] = len(selected_files)
            session_data['state'] = 'waiting_media_name'
            
            logger.info(f"用户 {user_id}: 选择了 {len(selected_files)} 个文件")
            
            message = f"✅ 已选择 {len(selected_files)} 个文件\n\n🎬 请输入剧名（如：老舅）"
            
            if skipped_ads:
                message += f"\n\n⚠️ 已自动跳过 {len(skipped_ads)} 个广告文件"
            
            self.wechat.send_text(user_id, message)
            
        except Exception as e:
            logger.error(f"选择文件失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 操作失败: {str(e)}")
    
    def _handle_media_name(self, user_id: str, content: str):
        """处理剧名输入"""
        session_data = self.user_sessions[user_id]
        media_name = content.strip()
        
        try:
            # 直接查询数据库
            from backend.models import get_session, CustomNameMapping
            from backend.api.quark_smart_transfer import QUARK_BASE_PATH, sessions
            
            db = get_session(self.db_engine)
            try:
                # 先尝试精确匹配
                mapping = db.query(CustomNameMapping).filter(
                    CustomNameMapping.original_name == media_name
                ).first()
                
                # 如果精确匹配失败，尝试模糊匹配
                if not mapping:
                    mapping = db.query(CustomNameMapping).filter(
                        CustomNameMapping.original_name.like(f"%{media_name.strip()}%")
                    ).first()
                
                if not mapping:
                    self.wechat.send_text(
                        user_id, 
                        f"❌ 未找到'{media_name}'的保存位置\n\n💡 请重新输入剧名，或发送新链接重新开始"
                    )
                    return
                
                # 构建路径
                quark_name = mapping.quark_name or media_name
                category = mapping.category or ''
                
                # 用户看到的路径
                display_path = f"/{category}/{quark_name}" if category else f"/{quark_name}"
                
                # OpenList完整路径
                full_path = f"{QUARK_BASE_PATH}/{category}/{quark_name}" if category else f"{QUARK_BASE_PATH}/{quark_name}"
                
                # 保存到会话
                session_id = session_data['session_id']
                session = sessions.get(session_id)
                if session:
                    session['media_name'] = media_name
                    session['display_path'] = display_path
                    session['full_path'] = full_path
                
                session_data['state'] = 'waiting_confirm'
                session_data['media_name'] = media_name
                session_data['target_path'] = display_path
                
                logger.info(f"用户 {user_id}: 查询到路径 {display_path}")
                
                message = f"""✅ 找到保存位置
                
📂 {display_path}

━━━━━━━━━━━━━━━
📋 转存信息：
• 剧名：{media_name}
• 文件：{session_data.get('selected_count', 0)}个
• 位置：{display_path}

━━━━━━━━━━━━━━━
确认转存请回复：确认
取消请回复：取消"""
                
                self.wechat.send_text(user_id, message)
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"查询路径失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 操作失败: {str(e)}")
    
    def _handle_confirm(self, user_id: str, content: str):
        """处理确认转存"""
        session_data = self.user_sessions[user_id]
        
        if content not in ['确认', '确定', 'ok', 'yes', 'y']:
            self.wechat.send_text(user_id, "❌ 已取消转存")
            # 清除会话
            del self.user_sessions[user_id]
            return
        
        try:
            # 执行转存
            self.wechat.send_text(user_id, "⏳ 正在转存，请稍候...")
            
            # 直接调用转存函数
            from backend.api.quark_smart_transfer import (
                sessions, get_target_fid_via_openlist, 
                call_quark_transfer_api, poll_quark_task
            )
            
            session_id = session_data['session_id']
            session = sessions.get(session_id)
            
            if not session:
                self.wechat.send_text(user_id, "❌ 会话已过期")
                del self.user_sessions[user_id]
                return
            
            # 获取目标文件夹ID
            logger.info(f"获取目标文件夹ID: {session['full_path']}")
            target_fid = get_target_fid_via_openlist(session['full_path'])
            session['target_fid'] = target_fid
            
            # 智能选择策略
            all_files = session['files']
            selected_files = session['selected_files']
            
            ratio = len(selected_files) / len(all_files)
            
            if ratio == 1:
                # 全选模式
                transfer_params = {'pdir_save_all': True, 'scene': 'link'}
                mode = "全选模式"
            elif ratio > 0.5:
                # 排除模式
                exclude_fids = [f['fid'] for f in all_files if f not in selected_files]
                transfer_params = {
                    'pdir_save_all': True,
                    'exclude_fids': exclude_fids,
                    'scene': 'link'
                }
                mode = "排除模式"
            else:
                # 包含模式
                transfer_params = {
                    'pdir_save_all': False,
                    'fid_list': [f['fid'] for f in selected_files],
                    'fid_token_list': [f['share_fid_token'] for f in selected_files],
                    'scene': 'link'
                }
                mode = "包含模式"
            
            logger.info(f"使用策略: {mode}, 比例: {ratio:.1%}")
            
            # 调用转存API
            task_id = call_quark_transfer_api(
                cookie=session['cookie'],
                stoken=session['stoken'],
                pwd_id=session['pwd_id'],
                pdir_fid=session['pdir_fid'],
                to_pdir_fid=target_fid,
                **transfer_params
            )
            
            logger.info(f"用户 {user_id}: 任务创建成功 {task_id}")
            
            # 轮询任务状态（异步执行，避免阻塞）
            import time
            max_retries = 30
            
            for i in range(max_retries):
                time.sleep(2)  # 每2秒查询一次
                
                try:
                    result = poll_quark_task(session['cookie'], task_id, timeout=2)
                    
                    # 转存完成
                    ad_filtered = len(all_files) - len(selected_files)
                    
                    message = f"""✅ 转存完成！

• 已保存：{len(selected_files)}个文件
• 已过滤：{ad_filtered}个广告
• 保存位置：{session.get('display_path', '')}
• 转存策略：{mode}"""
                    
                    self.wechat.send_text(user_id, message)
                    logger.info(f"用户 {user_id}: 转存完成")
                    
                    # 清除会话
                    del self.user_sessions[user_id]
                    return
                    
                except Exception as e:
                    # 任务还在进行中
                    if i < max_retries - 1:
                        continue
                    else:
                        # 最后一次还是失败，通知用户
                        logger.warning(f"轮询超时: {e}")
                        break
            
            # 超时
            self.wechat.send_text(user_id, "⚠️ 转存任务仍在进行中，请稍后在网盘中查看")
            del self.user_sessions[user_id]
            
        except Exception as e:
            logger.error(f"执行转存失败: {e}", exc_info=True)
            self.wechat.send_text(user_id, f"❌ 操作失败: {str(e)}")
            # 清除会话
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

