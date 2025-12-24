from fastapi import APIRouter
from pathlib import Path
from typing import List, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def scan_directory(path: Path, max_depth: int = 10) -> Dict[str, Any]:
    """
    扫描目录生成树结构
    
    Returns:
        {
            "name": "文件夹名",
            "path": "完整路径",
            "type": "directory",
            "size": 文件数量,
            "children": [...]
        }
    """
    if not path.exists():
        return None
    
    if path.is_file():
        return {
            "name": path.name,
            "path": str(path),
            "type": "file",
            "size": path.stat().st_size,
        }
    
    # 目录
    children = []
    total_size = 0
    
    try:
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name.startswith('.'):  # 跳过隐藏文件
                continue
            
            if item.is_dir():
                child = scan_directory(item, max_depth - 1) if max_depth > 0 else {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory",
                    "size": 0,
                    "children": []
                }
                if child:
                    children.append(child)
                    total_size += child.get('size', 0)
            else:
                child = {
                    "name": item.name,
                    "path": str(item),
                    "type": "file",
                    "size": item.stat().st_size,
                }
                children.append(child)
                total_size += child['size']
    except PermissionError:
        logger.warning(f"无权限访问: {path}")
    
    return {
        "name": path.name or str(path),
        "path": str(path),
        "type": "directory",
        "size": total_size,
        "file_count": len([c for c in children if c['type'] == 'file']),
        "dir_count": len([c for c in children if c['type'] == 'directory']),
        "children": children
    }


@router.get("/tree")
async def get_directory_tree(path: str, depth: int = 3):
    """获取目录树"""
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return {"success": False, "message": "目录不存在"}
        
        tree = scan_directory(dir_path, max_depth=depth)
        return {
            "success": True,
            "data": tree
        }
    except Exception as e:
        logger.error(f"获取目录树失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/file-list")
async def get_file_list(path: str):
    """获取目录下的文件列表（扁平化）"""
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return {"success": False, "message": "目录不存在"}
        
        files = []
        for item in dir_path.rglob('*'):
            if item.is_file() and not item.name.startswith('.'):
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime
                })
        
        return {
            "success": True,
            "total": len(files),
            "data": files
        }
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return {"success": False, "message": str(e)}
