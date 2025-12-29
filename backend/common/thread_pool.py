"""
全局线程池
避免每次请求创建新线程池
"""
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

# 全局线程池（用于CPU密集型或阻塞IO任务）
_executor: ThreadPoolExecutor = None


def get_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    """获取全局线程池"""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="app_worker")
        logger.info(f"✅ 全局线程池已创建 (max_workers={max_workers})")
    return _executor


def shutdown_executor():
    """关闭线程池"""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None
        logger.info("✅ 全局线程池已关闭")

