"""
网盘自动化API
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import logging

from backend.models import get_session

router = APIRouter()
logger = logging.getLogger(__name__)


def get_db():
    """依赖注入：获取数据库会话"""
    from backend.main import db_engine
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()


@router.post("/cloudpan/generate-links")
async def generate_share_links(
    background_tasks: BackgroundTasks,
    pan_type: str = 'baidu',
    target_path: Optional[str] = None,
    expire_days: int = 0,
    db: Session = Depends(get_db)
):
    """
    批量生成网盘分享链接
    
    Args:
        pan_type: 网盘类型（baidu/quark）
        target_path: 目标路径前缀（可选）
        expire_days: 有效期天数（0为永久）
    """
    try:
        # 添加后台任务
        background_tasks.add_task(
            _generate_links_task,
            pan_type,
            target_path,
            expire_days
        )
        
        return {
            "success": True,
            "message": f"已开始批量生成{pan_type}网盘分享链接，请在浏览器中完成登录操作"
        }
        
    except Exception as e:
        logger.error(f"启动生成任务失败: {e}")
        return {
            "success": False,
            "message": f"启动失败: {str(e)}"
        }


async def _generate_links_task(pan_type: str, target_path: Optional[str], expire_days: int):
    """后台任务：生成分享链接"""
    try:
        from backend.utils.cloudpan import CloudPanManager
        from backend.models import get_session
        from backend.main import db_engine
        
        logger.info(f"🚀 开始批量生成{pan_type}网盘分享链接...")
        
        manager = CloudPanManager(headless=False)  # 有头模式，方便用户登录
        
        # 获取数据库会话
        db = get_session(db_engine)
        try:
            results = await manager.batch_generate_links(
                db=db,
                pan_type=pan_type,
                target_path=target_path,
                expire_days=expire_days
            )
            
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"✅ 批量生成完成！成功: {success_count}/{len(results)}")
            
        finally:
            db.close()
            await manager.close_all()
            
    except Exception as e:
        logger.error(f"批量生成链接失败: {e}", exc_info=True)


@router.get("/cloudpan/status")
async def get_status():
    """
    获取网盘自动化状态
    """
    # TODO: 可以添加任务状态查询
    return {
        "success": True,
        "data": {
            "supported_pans": ["baidu", "quark"],
            "running": False  # 暂时硬编码
        }
    }
