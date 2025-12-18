"""
网盘自动化API
"""
from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import logging

from backend.models import get_session

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateLinksRequest(BaseModel):
    """生成链接请求"""
    pan_type: str = 'baidu'
    target_path: Optional[str] = None
    expire_days: int = 0
    original_name: Optional[str] = None  # 指定单个剧集名称


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
    request: GenerateLinksRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    批量生成网盘分享链接
    
    Args:
        request: 请求参数（包含pan_type, target_path, expire_days）
    """
    try:
        # 添加后台任务
        background_tasks.add_task(
            _generate_links_task,
            request.pan_type,
            request.target_path,
            request.expire_days,
            request.original_name
        )
        
        return {
            "success": True,
            "message": f"已开始批量生成{request.pan_type}网盘分享链接，请在浏览器中完成登录操作"
        }
        
    except Exception as e:
        logger.error(f"启动生成任务失败: {e}")
        return {
            "success": False,
            "message": f"启动失败: {str(e)}"
        }


async def _generate_links_task(pan_type: str, target_path: Optional[str], expire_days: int, original_name: Optional[str] = None):
    """后台任务：生成分享链接"""
    try:
        from backend.utils.cloudpan import CloudPanManager
        from backend.models import get_session
        from backend.main import db_engine
        
        if original_name:
            logger.info(f"🚀 开始为'{original_name}'生成{pan_type}网盘分享链接...")
        else:
            logger.info(f"🚀 开始批量生成{pan_type}网盘分享链接...")
        
        manager = CloudPanManager(headless=False)  # 有头模式，方便用户登录
        
        # 获取数据库会话
        db = get_session(db_engine)
        try:
            results = await manager.batch_generate_links(
                db=db,
                pan_type=pan_type,
                target_path=target_path,
                expire_days=expire_days,
                original_name=original_name  # 传递单个剧集名称
            )
            
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"✅ 批量生成完成！成功: {success_count}/{len(results)}")
            logger.info("ℹ️  浏览器保持打开状态，完成后请手动关闭。")
            
        finally:
            db.close()
            # 不自动关闭浏览器，方便用户检查结果
            # await manager.close_all()
            
    except Exception as e:
        logger.error(f"批量生成链接失败: {e}", exc_info=True)


@router.post("/cloudpan/upload-cookie")
async def upload_cookie(request: Request, pan_type: str):
    """
    上传网盘Cookie
    
    Args:
        request: FastAPI Request对象
        pan_type: 网盘类型（baidu/quark）
    """
    try:
        import json
        from pathlib import Path
        
        if pan_type not in ['baidu', 'quark']:
            return {
                "success": False,
                "message": "不支持的网盘类型"
            }
        
        # 获取请求体
        body = await request.body()
        cookie_data = body.decode('utf-8').strip()
        
        logger.info(f"收到cookie数据，长度: {len(cookie_data)}")
        
        # 解析JSON数组
        try:
            cookies = json.loads(cookie_data)
            if not isinstance(cookies, list):
                return {
                    "success": False,
                    "message": "Cookie格式错误，需要JSON数组格式"
                }
            
            logger.info(f"✅ 解析到{len(cookies)}个cookie")
            
            # 保存到文件
            cookies_dir = Path(__file__).parent.parent.parent / 'cookies'
            cookies_dir.mkdir(exist_ok=True)
            cookie_file = cookies_dir / f'{pan_type}_cookies.json'
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 已保存{pan_type}网盘Cookie到: {cookie_file}")
            
            return {
                "success": True,
                "message": f"{pan_type}网盘Cookie已保存成功 ({len(cookies)}个)"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {
                "success": False,
                "message": "Cookie格式错误，请确保是有效的JSON数组"
            }
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return {
                "success": False,
                "message": f"保存失败: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        return {
            "success": False,
            "message": f"请求失败: {str(e)}"
        }


@router.post("/cloudpan/import-baidu-links")
async def import_baidu_links(request: Request, db: Session = Depends(get_db)):
    """
    批量导入百度网盘链接（CSV格式）
    CSV格式: 文件名,链接,提取码,分享时间,分享状态
    """
    try:
        import csv
        import io
        from backend.models import CustomNameMapping
        
        # 获取CSV内容
        body = await request.body()
        csv_content = body.decode('utf-8')
        
        # 解析CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        success_count = 0
        skip_count = 0
        results = []
        
        for row in csv_reader:
            file_name = row.get('文件名', '').strip()
            link = row.get('链接', '').strip()
            pwd = row.get('提取码', '').strip()
            
            if not file_name or not link:
                continue
            
            # 格式化链接
            if pwd and '?pwd=' not in link:
                formatted_link = f"{link}?pwd={pwd} 提取码: {pwd}"
            elif '?pwd=' in link and pwd:
                formatted_link = f"{link} 提取码: {pwd}"
            else:
                formatted_link = link
            
            # 根据百度显示名查找映射
            mapping = db.query(CustomNameMapping).filter(
                CustomNameMapping.baidu_name == file_name
            ).first()
            
            if mapping:
                mapping.baidu_link = formatted_link
                db.commit()
                success_count += 1
                results.append(f"✅ {file_name}")
                logger.info(f"✅ 导入成功: {file_name} -> {formatted_link}")
            else:
                skip_count += 1
                results.append(f"⚠️ {file_name} (未找到匹配)")
                logger.warning(f"⚠️ 未找到映射: {file_name}")
        
        return {
            "success": True,
            "message": f"导入完成！成功: {success_count}, 跳过: {skip_count}",
            "details": results
        }
        
    except Exception as e:
        logger.error(f"导入百度链接失败: {e}")
        return {
            "success": False,
            "message": f"导入失败: {str(e)}"
        }


@router.post("/cloudpan/import-quark-links")
async def import_quark_links(request: Request, db: Session = Depends(get_db)):
    """
    批量导入夸克网盘链接（CSV格式）
    CSV格式: 序号,文件名,分享链接,提取码,状态
    """
    try:
        import csv
        import io
        from backend.models import CustomNameMapping
        
        # 获取CSV内容
        body = await request.body()
        csv_content = body.decode('utf-8')
        
        # 解析CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        success_count = 0
        skip_count = 0
        results = []
        
        for row in csv_reader:
            file_name = row.get('文件名', '').strip()
            link = row.get('分享链接', '').strip()
            pwd = row.get('提取码', '').strip()
            
            if not file_name or not link:
                continue
            
            # 夸克链接格式（通常没有提取码）
            formatted_link = link
            
            # 根据夸克显示名查找映射
            mapping = db.query(CustomNameMapping).filter(
                CustomNameMapping.quark_name == file_name
            ).first()
            
            if mapping:
                mapping.quark_link = formatted_link
                db.commit()
                success_count += 1
                results.append(f"✅ {file_name}")
                logger.info(f"✅ 导入成功: {file_name} -> {formatted_link}")
            else:
                skip_count += 1
                results.append(f"⚠️ {file_name} (未找到匹配)")
                logger.warning(f"⚠️ 未找到映射: {file_name}")
        
        return {
            "success": True,
            "message": f"导入完成！成功: {success_count}, 跳过: {skip_count}",
            "details": results
        }
        
    except Exception as e:
        logger.error(f"导入夸克链接失败: {e}")
        return {
            "success": False,
            "message": f"导入失败: {str(e)}"
        }


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
