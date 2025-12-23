"""
OpenList文件夹管理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
import requests

router = APIRouter()
logger = logging.getLogger(__name__)


class GetFolderIdRequest(BaseModel):
    """获取文件夹ID请求"""
    pan_type: str  # 'baidu', 'quark', 'xunlei'
    path: str      # 路径，如 /A-闲鱼影视/其他/综艺节目/测试


# OpenList配置
OPENLIST_URL = "http://10.10.10.17:5255"
OPENLIST_TOKEN = "openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4"

# 网盘挂载点
PAN_MOUNT_MAP = {
    'baidu': 'baidu',
    'quark': 'kuake',
    'xunlei': 'xunlei'
}


@router.post("/openlist/get-folder-id")
async def get_folder_id(request: GetFolderIdRequest):
    """
    获取文件夹ID，不存在则逐层创建
    
    逻辑：从unified_transfer.py的get_transfer_param复制
    """
    try:
        pan_type = request.pan_type
        user_path = request.path
        
        mount_point = PAN_MOUNT_MAP.get(pan_type)
        if not mount_point:
            raise HTTPException(status_code=400, detail=f"不支持的网盘类型: {pan_type}")
        
        # 构建完整路径
        full_path = f"/{mount_point}{user_path}"
        
        # 检查并创建目录
        parts = [p for p in full_path.split('/') if p]
        current_path = ""
        
        for idx, part in enumerate(parts, 1):
            current_path = f"{current_path}/{part}"
            parent_path = "/".join(current_path.split('/')[:-1]) or "/"
            
            # 列出父目录
            list_url = f"{OPENLIST_URL}/api/fs/list"
            list_headers = {"Authorization": OPENLIST_TOKEN}
            list_params = {"path": parent_path, "refresh": "false"}
            list_response = requests.get(list_url, params=list_params, headers=list_headers)
            data = list_response.json()
            content = data.get('content', [])
            
            found = False
            folder_id = None
            
            for item in content:
                if item.get('name') == part and item.get('is_dir'):
                    folder_id = item.get('id', '')
                    found = True
                    break
            
            # 如果不存在，创建目录
            if not found:
                mkdir_url = f"{OPENLIST_URL}/api/fs/mkdir"
                mkdir_headers = {"Authorization": OPENLIST_TOKEN, "Content-Type": "application/json"}
                mkdir_data = {"path": f"{parent_path}/{part}" if parent_path != "/" else f"/{part}"}
                mkdir_response = requests.post(mkdir_url, json=mkdir_data, headers=mkdir_headers)
                mkdir_result = mkdir_response.json()
                
                if mkdir_result.get('code') != 200:
                    raise Exception(f"创建目录失败: {mkdir_result.get('message')}")
                
                # 重新列出父目录，获取新建目录的ID
                list_response = requests.get(list_url, params=list_params, headers=list_headers)
                data = list_response.json()
                content = data.get('content', [])
                
                for item in content:
                    if item.get('name') == part and item.get('is_dir'):
                        folder_id = item.get('id', '')
                        break
                
                if not folder_id:
                    raise Exception(f"创建目录成功但无法获取ID: {part}")
            
            # 如果是最后一级，返回结果
            if idx == len(parts):
                if pan_type == 'baidu':
                    return {"success": True, "path": full_path, "fid": None}
                else:
                    if not folder_id:
                        raise Exception(f"文件夹ID为空: {current_path}")
                    return {"success": True, "fid": folder_id, "path": full_path}
        
        # fallback
        if pan_type == 'baidu':
            return {"success": True, "path": full_path, "fid": None}
        else:
            return {"success": False, "fid": None, "path": None}
            
    except Exception as e:
        logger.error(f"获取文件夹ID失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
