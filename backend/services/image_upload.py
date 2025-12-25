"""
图片上传服务
支持本地存储和图床（SM.MS等）
"""
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ImageUploadService:
    """图片上传服务"""
    
    def __init__(self, upload_type: str = "local", base_url: str = "http://localhost:8080"):
        """
        初始化
        
        Args:
            upload_type: 上传类型 local/smms
            base_url: 服务器地址
        """
        self.upload_type = upload_type
        self.base_url = base_url
        self.upload_dir = Path(__file__).parent.parent.parent / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_image(self, file_data: bytes, filename: str, custom_filename: Optional[str] = None) -> str:
        """
        上传图片
        
        Args:
            file_data: 文件数据
            filename: 原始文件名
            custom_filename: 自定义文件名
            
        Returns:
            图片URL
        """
        if self.upload_type == "smms":
            return await self._upload_to_smms(file_data, filename)
        else:
            return self._upload_to_local(file_data, filename, custom_filename)
    
    def _upload_to_local(self, file_data: bytes, filename: str, custom_filename: Optional[str] = None) -> str:
        """上传到本地"""
        # 生成文件名
        if custom_filename:
            final_filename = custom_filename
        else:
            timestamp = int(datetime.now().timestamp() * 1000)
            ext = Path(filename).suffix
            final_filename = f"{timestamp}_{filename}"
        
        # 保存文件
        file_path = self.upload_dir / final_filename
        file_path.write_bytes(file_data)
        
        # 返回 URL
        url = f"{self.base_url}/uploads/{final_filename}"
        logger.info(f"图片已上传到本地: {url}")
        return url
    
    async def _upload_to_smms(self, file_data: bytes, filename: str) -> str:
        """上传到 SM.MS 图床"""
        # TODO: 实现 SM.MS 上传
        raise NotImplementedError("SM.MS图床暂未实现，请使用本地存储")
    
    def delete_local_image(self, image_url: str) -> bool:
        """删除本地图片"""
        try:
            # 从 URL 提取文件名
            filename = image_url.split('/uploads/')[-1]
            file_path = self.upload_dir / filename
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"已删除图片: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除图片失败: {e}")
            return False

