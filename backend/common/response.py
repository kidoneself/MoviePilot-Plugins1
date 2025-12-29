"""
统一响应格式工具
"""
from typing import Any, Dict, Optional


class ResponseUtil:
    """API响应工具类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> Dict:
        """
        成功响应
        
        Args:
            data: 返回数据
            message: 提示信息
        
        Returns:
            标准响应格式
        """
        response = {
            "success": True,
            "message": message
        }
        
        if data is not None:
            response["data"] = data
        
        return response
    
    @staticmethod
    def error(message: str, code: int = 500, details: Any = None) -> Dict:
        """
        错误响应
        
        Args:
            message: 错误信息
            code: 错误码
            details: 详细错误信息
        
        Returns:
            标准响应格式
        """
        response = {
            "success": False,
            "message": message,
            "code": code
        }
        
        if details is not None:
            response["details"] = details
        
        return response
    
    @staticmethod
    def pan_transfer_success(
        pan_type: str,
        file_count: int,
        file_ids: list = None,
        message: str = "转存成功"
    ) -> Dict:
        """
        网盘转存成功响应（统一格式）
        
        Args:
            pan_type: 网盘类型
            file_count: 文件数量
            file_ids: 文件ID列表
            message: 提示信息
        
        Returns:
            转存响应格式
        """
        return {
            "success": True,
            "pan_type": pan_type,
            "file_count": file_count,
            "file_ids": file_ids or [],
            "message": message
        }
    
    @staticmethod
    def pan_transfer_error(
        pan_type: str,
        message: str,
        details: Any = None
    ) -> Dict:
        """
        网盘转存失败响应
        
        Args:
            pan_type: 网盘类型
            message: 错误信息
            details: 详细信息
        
        Returns:
            转存响应格式
        """
        response = {
            "success": False,
            "pan_type": pan_type,
            "file_count": 0,
            "file_ids": [],
            "message": message
        }
        
        if details:
            response["details"] = details
        
        return response

