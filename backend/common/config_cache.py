"""
配置缓存
启动时加载一次，避免重复读取文件
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class ConfigCache:
    """配置缓存（单例）"""
    _cat_config: Optional[Dict[str, Any]] = None
    _main_config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def load_cat_config(cls) -> Dict[str, Any]:
        """加载cat.yaml配置（缓存）"""
        if cls._cat_config is None:
            config_path = Path(__file__).resolve().parent.parent / 'cat.yaml'
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._cat_config = yaml.safe_load(f)
            logger.info(f"✅ cat.yaml配置已加载并缓存")
        return cls._cat_config
    
    @classmethod
    def load_main_config(cls) -> Dict[str, Any]:
        """加载config.yaml配置（缓存）"""
        if cls._main_config is None:
            import os
            config_path = os.getenv('CONFIG_PATH', 'config.yaml')
            if not os.path.isabs(config_path):
                base_dir = Path(__file__).parent.parent.parent
                config_path = base_dir / config_path
            
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._main_config = yaml.safe_load(f)
            logger.info(f"✅ config.yaml配置已加载并缓存")
        return cls._main_config
    
    @classmethod
    def reload_cat_config(cls) -> Dict[str, Any]:
        """重新加载cat.yaml（清除缓存）"""
        cls._cat_config = None
        return cls.load_cat_config()
    
    @classmethod
    def reload_main_config(cls) -> Dict[str, Any]:
        """重新加载config.yaml（清除缓存）"""
        cls._main_config = None
        return cls.load_main_config()
    
    @classmethod
    def get_cat_config(cls) -> Dict[str, Any]:
        """获取cat.yaml配置"""
        return cls.load_cat_config()
    
    @classmethod
    def get_main_config(cls) -> Dict[str, Any]:
        """获取config.yaml配置"""
        return cls.load_main_config()
    
    @classmethod
    def get_pansou_config(cls) -> Dict[str, Any]:
        """获取PanSou配置"""
        config = cls.get_main_config()
        return config.get('pansou', {})


# 方便的辅助函数
@lru_cache(maxsize=1)
def get_cat_config() -> Dict[str, Any]:
    """获取cat.yaml配置（带缓存）"""
    return ConfigCache.get_cat_config()


@lru_cache(maxsize=1)
def get_main_config() -> Dict[str, Any]:
    """获取config.yaml配置（带缓存）"""
    return ConfigCache.get_main_config()

