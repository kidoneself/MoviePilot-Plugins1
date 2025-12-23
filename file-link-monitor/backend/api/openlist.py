"""
OpenList文件夹管理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
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
    'quark': 'kuake',   # 注意：夸克在OpenList中是kuake
    'xunlei': 'xunlei'
}


def _list_directory(path: str) -> dict:
    """
    列出OpenList目录
    
    Args:
        path: 目录路径（如：/kuake/A-闲鱼影视）
    
    Returns:
        {
            "code": 200,
            "content": [
                {"name": "文件夹名", "is_dir": true, "id": "xxx"},
                ...
            ]
        }
    """
    url = f"{OPENLIST_URL}/api/fs/list"
    headers = {
        "Authorization": OPENLIST_TOKEN,
        "Content-Type": "application/json"
    }
    params = {"path": path, "refresh": "false"}
    
    response = requests.get(url, params=params, headers=headers)
    return response.json()


def _create_directory(parent_path: str, name: str) -> str:
    """
    创建OpenList目录
    
    Args:
        parent_path: 父目录路径（如：/kuake/A-闲鱼影视）
        name: 目录名称（如：其他）
    
    Returns:
        创建的目录ID
    """
    url = f"{OPENLIST_URL}/api/fs/mkdir"
    headers = {
        "Authorization": OPENLIST_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "path": f"{parent_path}/{name}" if parent_path != "/" else f"/{name}"
    }
    
    response = requests.post(url, json=data, headers=headers)
    result = response.json()
    
    if result.get('code') != 200:
        raise Exception(f"创建目录失败: {result.get('message')}")
    
    # 重新列出父目录，获取新建目录的ID
    list_data = _list_directory(parent_path)
    content = list_data.get('content', [])
    
    for item in content:
        if item.get('name') == name and item.get('is_dir'):
            return item.get('id', '')
    
    raise Exception(f"创建目录成功但无法获取ID: {name}")


@router.post("/openlist/get-folder-id")
async def get_folder_id(request: GetFolderIdRequest):
    """
    获取文件夹ID，不存在则逐层创建
    
    Args:
        request: {
            pan_type: 'baidu' | 'quark' | 'xunlei',
            path: '/A-闲鱼影视/其他/综艺节目/测试'
        }
    
    Returns:
        {
            "success": true,
            "fid": "xxx",  // 夸克/迅雷返回fid
            "path": "/kuake/A-闲鱼影视/其他/综艺节目/测试"  // OpenList中的完整路径
        }
    """
    try:
        pan_type = request.pan_type
        user_path = request.path
        
        # 获取挂载点
        mount_point = PAN_MOUNT_MAP.get(pan_type)
        if not mount_point:
            raise HTTPException(status_code=400, detail=f"不支持的网盘类型: {pan_type}")
        
        # 构建完整路径：/{挂载点}{用户路径}
        full_path = f"/{mount_point}{user_path}"
        logger.info(f"获取文件夹ID: {full_path}")
        
        # 分割路径
        parts = [p for p in full_path.split('/') if p]
        current_path = ""
        folder_id = None
        
        # 逐层检查并创建
        for idx, part in enumerate(parts, 1):
            current_path = f"{current_path}/{part}"
            parent_path = "/".join(current_path.split('/')[:-1]) or "/"
            
            logger.info(f"  检查目录: {current_path}")
            
            # 列出父目录
            data = _list_directory(parent_path)
            content = data.get('content', [])
            
            # 查找当前目录
            found = False
            for item in content:
                if item.get('name') == part and item.get('is_dir'):
                    folder_id = item.get('id', '')
                    found = True
                    logger.info(f"    ✅ 目录已存在, id: {folder_id}")
                    break
            
            # 不存在则创建
            if not found:
                logger.info(f"    ⚠️  目录不存在，正在创建...")
                folder_id = _create_directory(parent_path, part)
                logger.info(f"    ✅ 创建成功, id: {folder_id}")
        
        # 百度网盘返回路径，夸克/迅雷返回fid
        if pan_type == 'baidu':
            return {
                "success": True,
                "path": full_path,
                "fid": None
            }
        else:
            return {
                "success": True,
                "fid": folder_id,
                "path": full_path
            }
            
    except Exception as e:
        logger.error(f"获取文件夹ID失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
