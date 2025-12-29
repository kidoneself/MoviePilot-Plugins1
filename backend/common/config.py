"""
配置管理
统一从 config.yaml 读取配置
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器（单例模式）"""
    
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load(self, config_path: str = None) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为项目根目录的 config.yaml
        
        Returns:
            配置字典
        """
        if config_path is None:
            # 默认配置路径
            config_path = os.getenv('CONFIG_PATH', 'config.yaml')
            if not os.path.isabs(config_path):
                # 转为绝对路径
                base_dir = Path(__file__).parent.parent.parent
                config_path = str(base_dir / config_path)
        
        self._config_path = config_path
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项（支持点号分隔的嵌套key）
        
        Args:
            key: 配置键，支持 'a.b.c' 的形式
            default: 默认值
        
        Returns:
            配置值
        
        Examples:
            >>> config = ConfigManager()
            >>> config.load()
            >>> config.get('database.mysql.host')
            '101.35.224.59'
        """
        if self._config is None:
            self.load()
        
        # 支持点号分隔的嵌套访问
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_database_config(self) -> Dict:
        """获取数据库配置"""
        return self.get('database', {})
    
    def get_openlist_config(self) -> Dict:
        """
        获取 OpenList 配置
        注意：目前从 constants.py 读取，未来可以移到 config.yaml
        """
        from .constants import OPENLIST_URL, OPENLIST_TOKEN, OPENLIST_PATH_PREFIX
        return {
            'url': OPENLIST_URL,
            'token': OPENLIST_TOKEN,
            'path_prefix': OPENLIST_PATH_PREFIX
        }
    
    def get_notification_config(self) -> Dict:
        """获取通知配置"""
        return self.get('notification', {})
    
    def get_wechat_config(self) -> Dict:
        """获取企业微信配置"""
        return self.get('wechat', {})
    
    def reload(self) -> Dict:
        """重新加载配置文件"""
        if self._config_path:
            return self.load(self._config_path)
        return self.load()


# 全局配置管理器实例
config_manager = ConfigManager()

