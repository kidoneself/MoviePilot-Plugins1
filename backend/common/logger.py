"""
日志配置 - 支持环境变量控制日志级别
"""
import logging
import os
import sys


def setup_logging():
    """
    配置日志系统
    
    环境变量:
        LOG_LEVEL: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        默认: INFO
    
    生产环境建议:
        export LOG_LEVEL=WARNING  # 减少日志量，提升性能
    """
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # 验证日志级别
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level_str not in valid_levels:
        log_level_str = 'INFO'
    
    log_level = getattr(logging, log_level_str)
    
    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 降低第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('watchdog').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"✅ 日志系统已初始化: 级别={log_level_str}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称（通常使用 __name__）
    """
    return logging.getLogger(name)

