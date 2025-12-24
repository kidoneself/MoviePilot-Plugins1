"""
分享链接生成API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from backend.models import PanCookie, CustomNameMapping, get_session
from backend.utils.baidu_api import BaiduPanAPI
from backend.utils.quark_api import QuarkAPI
from backend.utils.xunlei_api import XunleiAPI

router = APIRouter()
logger = logging.getLogger(__name__)


class UpdateCookieRequest(BaseModel):
    """更新Cookie请求"""
    pan_type: str  # baidu/quark
    cookie: str


class GenerateLinkRequest(BaseModel):
    """生成链接请求"""
    pan_type: str  # baidu/quark
    original_name: Optional[str] = None  # 指定单个剧集，为空则批量处理


def get_db():
    """依赖注入：获取数据库会话"""
    from backend.main import db_engine
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()


@router.post('/cookie')
async def update_cookie(request: UpdateCookieRequest, db: Session = Depends(get_db)):
    """
    更新网盘Cookie
    """
    try:
        pan_type = request.pan_type.lower()
        if pan_type not in ['baidu', 'quark', 'xunlei']:
            raise HTTPException(status_code=400, detail="不支持的网盘类型")
        
        # 查找或创建
        cookie_obj = db.query(PanCookie).filter(PanCookie.pan_type == pan_type).first()
        
        if cookie_obj:
            # 更新现有Cookie
            cookie_obj.cookie = request.cookie
            cookie_obj.is_active = True
            cookie_obj.check_status = 'unknown'
            cookie_obj.check_error = None
            cookie_obj.last_check_time = None
            logger.info(f"更新{pan_type}网盘Cookie")
        else:
            # 创建新Cookie
            cookie_obj = PanCookie(
                pan_type=pan_type,
                cookie=request.cookie,
                is_active=True,
                check_status='unknown'
            )
            db.add(cookie_obj)
            logger.info(f"创建{pan_type}网盘Cookie")
        
        db.commit()
        
        return {
            'success': True,
            'message': f'{pan_type}网盘Cookie更新成功'
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新Cookie失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get('/cookie/{pan_type}')
async def get_cookie_status(pan_type: str, db: Session = Depends(get_db)):
    """
    获取Cookie状态
    """
    try:
        pan_type = pan_type.lower()
        cookie_obj = db.query(PanCookie).filter(PanCookie.pan_type == pan_type).first()
        
        if not cookie_obj:
            return {
                'exists': False,
                'is_active': False,
                'check_status': 'unknown'
            }
        
        return {
            'exists': True,
            'is_active': cookie_obj.is_active,
            'check_status': cookie_obj.check_status,
            'check_error': cookie_obj.check_error,
            'last_check_time': cookie_obj.last_check_time.isoformat() if cookie_obj.last_check_time else None
        }
        
    except Exception as e:
        logger.error(f"查询Cookie状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post('/generate-link')
async def generate_share_link(request: GenerateLinkRequest, db: Session = Depends(get_db)):
    """
    生成分享链接
    """
    try:
        pan_type = request.pan_type.lower()
        
        # 1. 获取Cookie
        cookie_obj = db.query(PanCookie).filter(
            PanCookie.pan_type == pan_type,
            PanCookie.is_active == True
        ).first()
        
        if not cookie_obj:
            raise HTTPException(status_code=400, detail=f"未配置{pan_type}网盘Cookie，请先上传")
        
        # 2. 查询要处理的映射
        query = db.query(CustomNameMapping).filter(CustomNameMapping.enabled == True)
        
        if request.original_name:
            # 单个剧集
            query = query.filter(CustomNameMapping.original_name == request.original_name)
            mappings = query.all()
            if not mappings:
                raise HTTPException(status_code=404, detail=f"未找到映射: {request.original_name}")
        else:
            # 批量处理：查找未生成链接的
            if pan_type == 'baidu':
                query = query.filter(
                    (CustomNameMapping.baidu_link == None) | (CustomNameMapping.baidu_link == '')
                )
            elif pan_type == 'quark':
                query = query.filter(
                    (CustomNameMapping.quark_link == None) | (CustomNameMapping.quark_link == '')
                )
            else:  # xunlei
                query = query.filter(
                    (CustomNameMapping.xunlei_link == None) | (CustomNameMapping.xunlei_link == '')
                )
            mappings = query.all()
        
        if not mappings:
            return {
                'success': True,
                'message': '没有需要处理的映射',
                'results': {}
            }
        
        # 3. 初始化API
        if pan_type == 'baidu':
            api = BaiduPanAPI(cookie_obj.cookie)
        elif pan_type == 'quark':
            api = QuarkAPI(cookie_obj.cookie)
        else:  # xunlei
            api = XunleiAPI(cookie_obj.cookie)
        
        # 4. 批量生成链接
        results = {}
        success_count = 0
        fail_count = 0
        
        for mapping in mappings:
            # 确定文件名
            if pan_type == 'baidu':
                folder_name = mapping.baidu_name or mapping.original_name
            elif pan_type == 'quark':
                folder_name = mapping.quark_name or mapping.original_name
            else:  # xunlei
                folder_name = mapping.xunlei_name or mapping.original_name
            
            logger.info(f"处理: {mapping.original_name} -> {folder_name}")
            
            # 生成链接
            link, error = api.generate_share_link(folder_name)
            
            if error:
                # 失败
                results[mapping.original_name] = {
                    'success': False,
                    'error': error
                }
                fail_count += 1
                logger.warning(f"❌ 失败: {mapping.original_name} - {error}")
            else:
                # 成功，更新数据库
                if pan_type == 'baidu':
                    mapping.baidu_link = link
                elif pan_type == 'quark':
                    mapping.quark_link = link
                else:  # xunlei
                    mapping.xunlei_link = link
                
                results[mapping.original_name] = {
                    'success': True,
                    'link': link
                }
                success_count += 1
                logger.info(f"✅ 成功: {mapping.original_name}")
        
        # 5. 提交数据库
        db.commit()
        
        return {
            'success': True,
            'message': f'处理完成：成功{success_count}个，失败{fail_count}个',
            'total': len(mappings),
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"生成链接失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成链接失败: {str(e)}")


@router.post("/pansou-search")
async def pansou_search(request: Request, db: Session = Depends(get_db)):
    """通过 PanSou API 搜索网盘资源"""
    try:
        import requests
        import yaml
        import os
        from pathlib import Path
        
        # 获取请求参数
        body = await request.json()
        keyword = body.get("keyword")
        
        if not keyword:
            raise HTTPException(status_code=400, detail="缺少搜索关键词")
        
        # 读取配置文件
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        if not os.path.isabs(config_path):
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / config_path
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        pansou_config = config.get("pansou", {})
        
        if not pansou_config.get("enabled"):
            raise HTTPException(status_code=400, detail="PanSou 功能未启用")
        
        pansou_url = pansou_config.get("url", "")
        pansou_token = pansou_config.get("token", "")
        cloud_types = pansou_config.get("cloud_types", ["baidu", "quark", "xunlei"])
        
        if not pansou_url:
            raise HTTPException(status_code=400, detail="PanSou API 地址未配置")
        
        # 构建 PanSou API 请求
        api_url = f"{pansou_url}/api/search"
        payload = {
            "kw": keyword,
            "res": "merge",
            "src": "all",
            "cloud_types": cloud_types
        }
        
        headers = {"Content-Type": "application/json"}
        if pansou_token:
            headers["Authorization"] = f"Bearer {pansou_token}"
        
        logger.info(f"搜索关键词: {keyword}, 网盘类型: {cloud_types}")
        
        # 第一次搜索：快速返回缓存结果
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"PanSou API 请求失败: {response.status_code}, {response.text}")
            raise HTTPException(status_code=500, detail=f"搜索失败: {response.text}")
        
        data = response.json()
        result_data = data.get("data", {})
        first_total = result_data.get("total", 0)
        
        logger.info(f"首次搜索: 找到 {first_total} 条缓存结果，等待异步搜索完成...")
        
        # 等待3秒，让异步插件搜索完成
        import time
        time.sleep(3)
        
        # 第二次搜索：获取完整结果
        response2 = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response2.status_code != 200:
            logger.warning(f"第二次搜索失败，使用首次结果")
            final_data = data
        else:
            final_data = response2.json()
        
        # 解析最终结果
        result_data = final_data.get("data", {})
        total = result_data.get("total", 0)
        merged_by_type = result_data.get("merged_by_type", {})
        
        logger.info(f"搜索完成: 找到 {total} 条结果（首次 {first_total} 条）")
        
        return {
            "success": True,
            "total": total,
            "results": merged_by_type
        }
        
    except requests.exceptions.Timeout:
        logger.error("PanSou API 请求超时")
        raise HTTPException(status_code=500, detail="搜索超时")
    except requests.exceptions.RequestException as e:
        logger.error(f"PanSou API 请求异常: {e}")
        raise HTTPException(status_code=500, detail=f"请求异常: {str(e)}")
    except Exception as e:
        logger.error(f"PanSou 搜索失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today-share-text")
def get_today_share_text(db: Session = Depends(get_db)):
    """生成今日更新分享文案"""
    try:
        from datetime import date
        from sqlalchemy import func
        from backend.models import LinkRecord
        
        today = date.today()
        
        # 查询今日更新的记录，按剧集分组
        records = db.query(LinkRecord).filter(
            func.date(LinkRecord.created_at) == today
        ).order_by(LinkRecord.original_name).all()
        
        if not records:
            return {
                "success": True,
                "text": f"【{today.strftime('%Y-%m-%d')} 今日更新】\n\n暂无更新"
            }
        
        # 按剧名分组统计
        show_updates = {}
        for record in records:
            show_name = record.original_name
            if show_name not in show_updates:
                show_updates[show_name] = {
                    "files": [],
                    "episodes": set()
                }
            
            # 提取集数
            import re
            file_name = record.source_file.split('/')[-1]
            ep_match = re.search(r'[SE](\d+)[E.](\d+)', file_name, re.IGNORECASE)
            if ep_match:
                episode = int(ep_match.group(2))
                show_updates[show_name]["episodes"].add(episode)
            
            show_updates[show_name]["files"].append(file_name)
        
        # 获取分享链接
        mappings = db.query(CustomNameMapping).filter(
            CustomNameMapping.original_name.in_(list(show_updates.keys()))
        ).all()
        
        mapping_dict = {m.original_name: m for m in mappings}
        
        # 生成文案
        import re
        lines = [f"【{today.strftime('%Y-%m-%d')} 今日更新】\n"]
        
        for show_name in sorted(show_updates.keys()):
            episodes = sorted(show_updates[show_name]["episodes"])
            mapping = mapping_dict.get(show_name)
            
            # 剧名和更新信息
            if episodes:
                ep_str = f"更新{episodes[-1]:02d}" if len(episodes) == 1 else f"更新{episodes[0]:02d}-{episodes[-1]:02d}"
            else:
                ep_str = f"更新{len(show_updates[show_name]['files'])}个文件"
            
            # 是否完结
            completed_tag = "【完结】" if mapping and mapping.is_completed else ""
            
            lines.append(f"{show_name} {ep_str}{completed_tag}")
            
            # 分享链接（直接使用数据库原始值）
            if mapping:
                if mapping.baidu_link:
                    lines.append(f"BD：{mapping.baidu_link}")
                
                if mapping.quark_link:
                    lines.append(f"KK：{mapping.quark_link}")
                
                if mapping.xunlei_link:
                    lines.append(f"XL：{mapping.xunlei_link}")
            
            lines.append("")  # 空行分隔
        
        text = "\n".join(lines)
        
        return {
            "success": True,
            "text": text
        }
    except Exception as e:
        logger.error(f"生成今日分享文案失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/share-links")
def get_all_share_links(db: Session = Depends(get_db)):
    """获取所有剧集的分享链接"""
    try:
        # 查询所有有分享链接的映射
        mappings = db.query(CustomNameMapping).filter(
            (CustomNameMapping.baidu_link.isnot(None)) |
            (CustomNameMapping.quark_link.isnot(None)) |
            (CustomNameMapping.xunlei_link.isnot(None))
        ).order_by(CustomNameMapping.updated_at.desc()).all()
        
        result = []
        for mapping in mappings:
            # 直接返回数据库原始值，不做任何处理
            item = {
                "original_name": mapping.original_name,
                "is_completed": mapping.is_completed or False,
                "baidu_link": mapping.baidu_link,
                "quark_link": mapping.quark_link,
                "xunlei_link": mapping.xunlei_link
            }
            result.append(item)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"获取分享链接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
