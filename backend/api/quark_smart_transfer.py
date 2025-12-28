"""
夸克智能转存API

完整流程：
1. 解析分享链接 -> 返回文件列表（标记广告）
2. 选择文件
3. 输入剧名 -> 查询目标路径
4. 用户确认 -> 执行转存
5. 轮询任务状态
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import requests
import re
import time
import uuid
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

# 会话存储（生产环境建议用Redis）
sessions = {}

# 配置
OPENLIST_URL = 'http://10.10.10.17:5255'
OPENLIST_TOKEN = 'openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4'
QUARK_BASE_PATH = '/A-闲鱼影视（自动更新）'  # 夸克网盘基础路径


# ==================== 数据模型 ====================

class ParseShareRequest(BaseModel):
    """解析分享链接请求"""
    share_url: str


class SelectFilesRequest(BaseModel):
    """选择文件请求"""
    session_id: str
    selection: str  # "all" 或 "1,3,5-10"


class GetTargetPathRequest(BaseModel):
    """查询目标路径请求"""
    session_id: str
    media_name: str


class ExecuteTransferRequest(BaseModel):
    """执行转存请求"""
    session_id: str


class FileInfo(BaseModel):
    """文件信息"""
    index: int
    fid: str
    name: str
    size: int
    is_ad: bool
    share_fid_token: str


# ==================== 工具函数 ====================

def get_cookie_from_db() -> str:
    """从数据库获取夸克Cookie"""
    from backend.models import get_session, PanCookie
    from backend.main import db_engine
    
    db = get_session(db_engine)
    try:
        cookie_obj = db.query(PanCookie).filter(
            PanCookie.pan_type == 'quark',
            PanCookie.is_active == True
        ).first()
        
        if not cookie_obj:
            raise Exception("未找到夸克Cookie")
        
        cookie = cookie_obj.cookie
        
        # 处理JSON格式的Cookie
        if isinstance(cookie, str) and cookie.startswith('['):
            import json
            cookie_list = json.loads(cookie)
            cookie = "; ".join([f"{c['name']}={c['value']}" for c in cookie_list])
        
        return cookie
    finally:
        db.close()


def parse_share_url(share_url: str) -> tuple:
    """解析分享URL，返回(pwd_id, pdir_fid)"""
    pwd_match = re.search(r'/s/([a-zA-Z0-9]+)', share_url)
    if not pwd_match:
        raise ValueError("无法从URL中提取pwd_id")
    pwd_id = pwd_match.group(1)
    
    pdir_fid = '0'  # 默认根目录
    if '#/list/share/' in share_url:
        fid_part = share_url.split('#/list/share/')[-1].split('?')[0]
        if fid_part:
            pdir_fid = fid_part
    
    return pwd_id, pdir_fid


def get_quark_stoken(cookie: str, pwd_id: str) -> str:
    """获取夸克stoken"""
    url = 'https://drive-h.quark.cn/1/clouddrive/share/sharepage/token'
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': ''
    }
    body = {
        'pwd_id': pwd_id
    }
    headers = {
        'Cookie': cookie,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://pan.quark.cn/s/{pwd_id}'
    }
    
    resp = requests.post(url, params=params, json=body, headers=headers)
    
    if resp.status_code != 200:
        raise Exception(f"获取stoken失败: HTTP {resp.status_code}")
    
    data = resp.json()
    if data.get('code') != 0:
        raise Exception(f"获取stoken失败: {data.get('message')}")
    
    return data['data']['stoken']


def get_quark_file_list(cookie: str, pwd_id: str, stoken: str, pdir_fid: str) -> dict:
    """获取夸克文件列表"""
    url = 'https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail'
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': '',
        'ver': '2',
        'pwd_id': pwd_id,
        'stoken': stoken,
        'pdir_fid': pdir_fid,
        'force': '0',
        '_page': 1,
        '_size': 50,
        '_fetch_banner': 1,
        '_fetch_share': 1,
        'fetch_relate_conversation': 1,
        '_fetch_total': 1,
        '_sort': 'file_type:asc,file_name:asc'
    }
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://pan.quark.cn/s/{pwd_id}',
        'Accept': 'application/json, text/plain, */*'
    }
    
    resp = requests.get(url, params=params, headers=headers)
    
    if resp.status_code != 200:
        raise Exception(f"获取文件列表失败: HTTP {resp.status_code}")
    
    data = resp.json()
    if data.get('code') != 0:
        raise Exception(f"获取文件列表失败: {data.get('message')}")
    
    files = data['data'].get('list', [])
    total = data['data'].get('total', len(files))
    
    return {
        'files': files,
        'total': total
    }


def is_ad_file(file_name: str, file_size: int) -> bool:
    """判断是否为广告文件"""
    AD_KEYWORDS = [
        '群', '更新', '关注', '订阅', '微信', 'qq', '频道', '电报', 'telegram', '推荐', '福利', '免费',
        '网址', '网站', '发布', '必看', '说明', '广告', '二维码', '热门影视', '资源', '入群', '扫码',
        '夸克资源', '阿里资源', '百度资源', '更多资源', '公众号', '最新', 'vx', 'wx',
        'readme', 'read me', 'notice', 'ad', 'ads', 'adv', 'promo', 'promotion', 'follow', 'subscribe',
        'update', 'new', 'latest', 'channel', 'qrcode', 'discord', 'tg'
    ]
    AD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.txt', '.nfo', '.url']
    
    name_lower = file_name.lower()
    ext = None
    if '.' in name_lower:
        ext = name_lower[name_lower.rfind('.'):]
    
    if ext in AD_EXTENSIONS:
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            if file_size < 5 * 1024 * 1024:  # 5MB
                for keyword in AD_KEYWORDS:
                    if keyword in name_lower:
                        return True
        elif ext in ['.txt', '.nfo', '.url']:
            if file_size < 500 * 1024:  # 500KB
                return True
    
    SUSPICIOUS_PATTERNS = ['热门影视更新', '资源更新', '最新资源', '关注获取', '扫码进群', '加入频道']
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in name_lower:
            return True
    
    return False


def get_target_fid_via_openlist(target_path: str) -> str:
    """通过OpenList获取目标文件夹ID（不存在则创建）"""
    headers = {"Authorization": OPENLIST_TOKEN, "Content-Type": "application/json"}
    
    # 构建完整路径
    full_path = f"/kuake{target_path}"
    
    # 逐层检查和创建目录
    parts = [p for p in full_path.split('/') if p]
    current_path = ""
    
    for idx, part in enumerate(parts, 1):
        current_path = f"{current_path}/{part}"
        parent_path = "/".join(current_path.split('/')[:-1]) or "/"
        
        # 列出父目录
        list_url = f"{OPENLIST_URL}/api/fs/list"
        body = {"path": parent_path, "refresh": False, "page": 1, "per_page": 1000}
        
        resp = requests.post(list_url, json=body, headers=headers)
        result = resp.json()
        
        if result.get('code') != 200:
            raise Exception(f"列出目录失败: {result.get('message')}")
        
        content = result.get('data', {}).get('content') or []
        
        # 查找目标文件夹
        found = False
        folder_id = None
        
        for item in content:
            is_mount = item.get('mount_details') is not None
            is_directory = item.get('is_dir') == True
            item_name = item.get('name', '').strip()
            
            if item_name == part.strip() and (is_directory or is_mount):
                folder_id = item.get('id', '')
                found = True
                logger.info(f"OpenList: 找到目录 {part}, id={folder_id}")
                break
        
        # 不存在则创建
        if not found:
            logger.info(f"OpenList: 创建目录 {part}")
            mkdir_path = f"{parent_path}/{part}" if parent_path != "/" else f"/{part}"
            mkdir_url = f"{OPENLIST_URL}/api/fs/mkdir"
            mkdir_body = {"path": mkdir_path}
            
            mkdir_resp = requests.post(mkdir_url, json=mkdir_body, headers=headers)
            mkdir_result = mkdir_resp.json()
            
            if mkdir_result.get('code') != 200:
                raise Exception(f"创建目录失败: {mkdir_result.get('message')}")
            
            # 重新列出，获取新建目录的ID
            resp = requests.post(list_url, json=body, headers=headers)
            result = resp.json()
            content = result.get('data', {}).get('content') or []
            
            for item in content:
                if item.get('name', '').strip() == part.strip() and item.get('is_dir'):
                    folder_id = item.get('id', '')
                    logger.info(f"OpenList: 创建成功，id={folder_id}")
                    break
            
            if not folder_id:
                raise Exception(f"创建目录后无法获取ID: {part}")
    
    logger.info(f"OpenList: 最终文件夹ID={folder_id}")
    return folder_id


def call_quark_transfer_api(cookie: str, stoken: str, pwd_id: str, pdir_fid: str, 
                            to_pdir_fid: str, **params) -> str:
    """调用夸克转存API"""
    url = 'https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save'
    query_params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': ''
    }
    body = {
        'pwd_id': pwd_id,
        'stoken': stoken,
        'pdir_fid': pdir_fid,
        'to_pdir_fid': to_pdir_fid,
        'scene': 'link',
        **params
    }
    headers = {
        'Cookie': cookie,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://pan.quark.cn/s/{pwd_id}'
    }
    
    logger.info(f"夸克转存参数: {body}")
    
    resp = requests.post(url, params=query_params, json=body, headers=headers)
    data = resp.json()
    
    if data.get('code') != 0:
        raise Exception(f"转存失败: {data.get('message')}")
    
    return data['data']['task_id']


def poll_quark_task(cookie: str, task_id: str, timeout: int = 60) -> dict:
    """轮询夸克任务状态"""
    url = 'https://drive-pc.quark.cn/1/clouddrive/task'
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    start_time = time.time()
    retry = 0
    
    while time.time() - start_time < timeout:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            'task_id': task_id,
            'retry_index': retry
        }
        
        resp = requests.get(url, params=params, headers=headers)
        data = resp.json()
        
        if data.get('code') != 0:
            raise Exception(f"查询任务失败: {data.get('message')}")
        
        status = data['data']['status']
        logger.info(f"任务状态: {status} (重试: {retry})")
        
        if status == 2:  # 完成
            return data['data']
        elif status in [0, 1]:  # 进行中
            time.sleep(1)
            retry += 1
        else:  # 其他状态
            raise Exception(f"任务失败: {data['data'].get('message', '未知错误')}")
        
        retry += 1
        time.sleep(0.5)
    
    raise Exception("任务超时")


def parse_file_selection(selection: str, total: int) -> set:
    """解析文件选择（如：1,3,5-10）"""
    if selection.lower() in ['all', 'a', '全部']:
        return set(range(1, total + 1))
    
    indices = set()
    for part in selection.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            indices.update(range(int(start), int(end) + 1))
        else:
            indices.add(int(part))
    
    return indices


def clean_session_data():
    """清理过期会话（超过1小时）"""
    now = datetime.now()
    expired_keys = [
        key for key, value in sessions.items()
        if (now - value.get('created_at', now)).total_seconds() > 3600
    ]
    for key in expired_keys:
        del sessions[key]


# ==================== API 接口 ====================

@router.post("/quark/parse-share")
async def parse_share(request: ParseShareRequest):
    """
    步骤1: 解析分享链接，返回文件列表（标记广告）
    """
    try:
        clean_session_data()
        
        # 解析URL
        pwd_id, pdir_fid = parse_share_url(request.share_url)
        
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
            'share_url': request.share_url,
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
        
        logger.info(f"创建会话: {session_id}, 文件数: {len(files)}")
        
        return {
            'success': True,
            'session_id': session_id,
            'files': files,
            'stats': {
                'total': len(files),
                'ad_count': ad_count,
                'clean_count': clean_count
            }
        }
        
    except Exception as e:
        logger.error(f"解析分享链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quark/select-files")
async def select_files(request: SelectFilesRequest):
    """
    步骤2: 选择要转存的文件
    """
    try:
        # 获取会话
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        # 解析选择
        total_files = len(session['files'])
        selected_indices = parse_file_selection(request.selection, total_files)
        
        # 过滤文件（排除广告和文件夹）
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
        
        logger.info(f"会话 {request.session_id}: 选择了 {len(selected_files)} 个文件")
        
        return {
            'success': True,
            'selected_count': len(selected_files),
            'skipped_ads': skipped_ads,
            'message': f"已选择 {len(selected_files)} 个文件，请输入剧名"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"选择文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quark/get-target-path")
async def get_target_path(request: GetTargetPathRequest):
    """
    步骤3: 根据剧名查询目标路径
    """
    try:
        from backend.models import get_session, CustomNameMapping
        from backend.main import db_engine
        
        # 获取会话
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        # 查询映射表
        db = get_session(db_engine)
        try:
            # 先尝试精确匹配
            mapping = db.query(CustomNameMapping).filter(
                CustomNameMapping.original_name == request.media_name
            ).first()
            
            # 如果精确匹配失败，尝试模糊匹配
            if not mapping:
                mappings = db.query(CustomNameMapping).filter(
                    CustomNameMapping.original_name.like(f"%{request.media_name.strip()}%")
                ).all()
                
                if not mappings:
                    return {
                        'success': False,
                        'error': '未找到剧名映射',
                        'message': f"未找到'{request.media_name}'的保存位置，请先配置映射关系"
                    }
                elif len(mappings) > 1:
                    # 多个匹配，返回选项列表
                    options = [
                        {
                            'id': m.id,
                            'original_name': m.original_name,
                            'quark_name': m.quark_name or m.original_name,
                            'category': m.category or ''
                        }
                        for m in mappings
                    ]
                    return {
                        'success': False,
                        'error': '多个匹配',
                        'message': f"找到 {len(mappings)} 个匹配的剧名，请选择",
                        'options': options
                    }
                else:
                    # 只有一个匹配
                    mapping = mappings[0]
            
            if not mapping:
                return {
                    'success': False,
                    'error': '未找到剧名映射',
                    'message': f"未找到'{request.media_name}'的保存位置，请先配置映射关系"
                }
            
            # 构建路径
            quark_name = mapping.quark_name or request.media_name
            category = mapping.category or ''
            
            # 用户看到的路径
            display_path = f"/{category}/{quark_name}" if category else f"/{quark_name}"
            
            # OpenList完整路径
            full_path = f"{QUARK_BASE_PATH}/{category}/{quark_name}" if category else f"{QUARK_BASE_PATH}/{quark_name}"
            
            # 保存到会话
            session['media_name'] = request.media_name
            session['display_path'] = display_path
            session['full_path'] = full_path
            
            logger.info(f"会话 {request.session_id}: 查询到路径 {display_path}")
            
            return {
                'success': True,
                'media_name': request.media_name,
                'quark_name': quark_name,
                'category': category,
                'display_path': display_path,
                'full_path': full_path,
                'message': f"将保存到：{display_path}\n\n确认请回复：确认"
            }
            
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询目标路径失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quark/execute-transfer")
async def execute_transfer(request: ExecuteTransferRequest):
    """
    步骤4: 执行转存
    """
    try:
        # 获取会话
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        if not session.get('selected_files'):
            raise HTTPException(status_code=400, detail="未选择文件")
        
        if not session.get('full_path'):
            raise HTTPException(status_code=400, detail="未设置目标路径")
        
        # 通过OpenList获取目标文件夹ID
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
        
        session['task_id'] = task_id
        session['mode'] = mode
        session['transfer_started_at'] = datetime.now()
        
        logger.info(f"会话 {request.session_id}: 任务创建成功 {task_id}")
        
        return {
            'success': True,
            'task_id': task_id,
            'mode': mode,
            'message': '正在转存，请稍候...'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行转存失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quark/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    步骤5: 查询任务状态
    """
    try:
        # 查找会话
        session = None
        for s in sessions.values():
            if s.get('task_id') == task_id:
                session = s
                break
        
        if not session:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 查询任务状态
        result = poll_quark_task(session['cookie'], task_id, timeout=2)
        
        # 任务完成
        ad_filtered = len(session['files']) - len(session['selected_files'])
        
        logger.info(f"任务 {task_id}: 完成")
        
        return {
            'success': True,
            'status': 'completed',
            'transferred': len(session['selected_files']),
            'ad_filtered': ad_filtered,
            'display_path': session.get('display_path', ''),
            'mode': session.get('mode', ''),
            'message': f"✅ 转存完成！\n• 已保存：{len(session['selected_files'])}个文件\n• 已过滤：{ad_filtered}个广告\n• 保存位置：{session.get('display_path', '')}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # 如果是超时或任务仍在进行，返回处理中状态
        if '超时' in str(e) or '进行中' in str(e):
            return {
                'success': True,
                'status': 'processing',
                'message': '转存中，请继续等待...'
            }
        
        logger.error(f"查询任务状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quark/list-media-names")
async def list_media_names():
    """
    辅助接口：获取所有可用的剧名列表
    """
    try:
        from backend.models import get_session, CustomNameMapping
        from backend.main import db_engine
        
        db = get_session(db_engine)
        try:
            mappings = db.query(CustomNameMapping).filter(
                CustomNameMapping.enabled == True
            ).all()
            
            media_names = [m.original_name for m in mappings]
            
            return {
                'success': True,
                'media_names': media_names,
                'total': len(media_names)
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"获取剧名列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

