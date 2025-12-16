from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
import logging

from backend.models import LinkRecord, get_session

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


@router.get("/records")
async def get_records(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    group_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取硬链接记录"""
    try:
        query = db.query(LinkRecord)
        
        # 状态筛选
        if status:
            query = query.filter(LinkRecord.status == status)
        
        # 总数
        total = query.count()
        
        # 分页
        records = query.order_by(desc(LinkRecord.created_at))\
                      .offset((page - 1) * page_size)\
                      .limit(page_size)\
                      .all()
        
        # 按源目录分组
        if group_by == "source_dir":
            from pathlib import Path
            from collections import defaultdict
            
            groups = defaultdict(list)
            
            for record in records:
                # 获取源文件的父目录名称
                source_path = Path(record.source_file)
                parent_name = source_path.parent.name if source_path.parent.name else "根目录"
                
                groups[parent_name].append({
                    "id": record.id,
                    "source_file": record.source_file,
                    "target_file": record.target_file,
                    "file_size": record.file_size,
                    "link_method": record.link_method,
                    "status": record.status,
                    "error_msg": record.error_msg,
                    "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 转换为列表格式
            grouped_data = []
            for dir_name, items in groups.items():
                grouped_data.append({
                    "dir_name": dir_name,
                    "count": len(items),
                    "records": items
                })
            
            return {
                "success": True,
                "total": total,
                "page": page,
                "page_size": page_size,
                "grouped": True,
                "data": grouped_data
            }
        
        # 不分组，返回原格式
        data = []
        for record in records:
            data.append({
                "id": record.id,
                "source_file": record.source_file,
                "target_file": record.target_file,
                "file_size": record.file_size,
                "link_method": record.link_method,
                "status": record.status,
                "error_msg": record.error_msg,
                "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "success": True,
            "total": total,
            "page": page,
            "page_size": page_size,
            "grouped": False,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取记录失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """获取统计信息"""
    try:
        # 总记录数
        total_records = db.query(func.count(LinkRecord.id)).scalar()
        
        # 成功/失败数
        success_count = db.query(func.count(LinkRecord.id))\
                         .filter(LinkRecord.status == 'success').scalar()
        failed_count = db.query(func.count(LinkRecord.id))\
                        .filter(LinkRecord.status == 'failed').scalar()
        
        # 总大小
        total_size = db.query(func.sum(LinkRecord.file_size))\
                      .filter(LinkRecord.status == 'success').scalar() or 0
        
        # 今天的记录
        from datetime import datetime, timedelta
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(func.count(LinkRecord.id))\
                       .filter(LinkRecord.created_at >= today).scalar()
        
        # 最近10条记录
        recent = db.query(LinkRecord)\
                  .order_by(desc(LinkRecord.created_at))\
                  .limit(10)\
                  .all()
        
        recent_data = []
        for r in recent:
            recent_data.append({
                "source_file": r.source_file,
                "target_file": r.target_file,
                "file_size": r.file_size,
                "status": r.status,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "success": True,
            "data": {
                "total_records": total_records,
                "success_count": success_count,
                "failed_count": failed_count,
                "total_size": total_size,
                "today_count": today_count,
                "recent": recent_data
            }
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {"success": False, "message": str(e)}


@router.delete("/records/{record_id}")
async def delete_record(record_id: int, db: Session = Depends(get_db)):
    """删除记录"""
    try:
        record = db.query(LinkRecord).filter(LinkRecord.id == record_id).first()
        if not record:
            return {"success": False, "message": "记录不存在"}
        
        db.delete(record)
        db.commit()
        
        return {"success": True, "message": "删除成功"}
    except Exception as e:
        logger.error(f"删除记录失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/records/{record_id}/retry")
async def retry_link(record_id: int, db: Session = Depends(get_db)):
    """重试硬链接"""
    try:
        from pathlib import Path
        from backend.utils.linker import FileLinker
        from datetime import datetime
        import yaml
        
        # 获取记录
        record = db.query(LinkRecord).filter(LinkRecord.id == record_id).first()
        if not record:
            return {"success": False, "message": "记录不存在"}
        
        source_file = Path(record.source_file)
        target_file = Path(record.target_file)
        
        # 检查源文件是否存在
        if not source_file.exists():
            return {"success": False, "message": "源文件不存在"}
        
        # 从配置文件读取混淆设置
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 查找该源文件所属的监控配置
        obfuscate_enabled = False
        for monitor in config.get('monitors', []):
            source_dir = Path(monitor['source'])
            if source_file.is_relative_to(source_dir):
                obfuscate_enabled = monitor.get('obfuscate_enabled', False)
                break
        
        # 重新创建硬链接（使用混淆设置）
        linker = FileLinker(obfuscate_enabled=obfuscate_enabled)
        success, method, error = linker.create_hardlink(source_file, target_file)
        
        # 更新记录
        record.link_method = method
        record.status = "success" if success else "failed"
        record.error_msg = error
        record.created_at = datetime.now()
        
        db.commit()
        
        if success:
            return {
                "success": True,
                "message": f"重试成功，使用{method}方式"
            }
        else:
            return {
                "success": False,
                "message": f"重试失败：{error}"
            }
    except Exception as e:
        logger.error(f"重试硬链接失败: {e}")
        db.rollback()
        return {"success": False, "message": str(e)}


@router.post("/records/{record_id}/resync")
async def resync_link(record_id: int, db: Session = Depends(get_db)):
    """重新同步（删除记录并重新创建硬链接）"""
    try:
        from pathlib import Path
        from backend.utils.linker import FileLinker
        from datetime import datetime
        import yaml
        
        # 获取记录
        record = db.query(LinkRecord).filter(LinkRecord.id == record_id).first()
        if not record:
            return {"success": False, "message": "记录不存在"}
        
        source_file = Path(record.source_file)
        target_file = Path(record.target_file)
        
        # 检查源文件是否存在
        if not source_file.exists():
            return {"success": False, "message": "源文件不存在"}
        
        # 从配置文件读取混淆设置
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 查找该源文件所属的监控配置
        obfuscate_enabled = False
        for monitor in config.get('monitors', []):
            source_dir = Path(monitor['source'])
            if source_file.is_relative_to(source_dir):
                obfuscate_enabled = monitor.get('obfuscate_enabled', False)
                break
        
        # 删除旧记录
        db.delete(record)
        db.commit()
        
        # 重新创建硬链接（使用混淆设置）
        linker = FileLinker(obfuscate_enabled=obfuscate_enabled)
        success, method, error = linker.create_hardlink(source_file, target_file)
        
        # 创建新记录
        new_record = LinkRecord(
            source_file=str(source_file),
            target_file=str(target_file),
            file_size=source_file.stat().st_size,
            link_method=method,
            status="success" if success else "failed",
            error_msg=error
        )
        db.add(new_record)
        db.commit()
        
        if success:
            return {
                "success": True,
                "message": f"重新同步成功，使用{method}方式"
            }
        else:
            return {
                "success": False,
                "message": f"重新同步失败：{error}"
            }
    except Exception as e:
        logger.error(f"重新同步失败: {e}")
        db.rollback()
        return {"success": False, "message": str(e)}
