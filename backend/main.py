import os
import yaml
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
from backend.common.static_files import CachedStaticFiles

from backend.models import init_database
from backend.monitor import MonitorService
from backend.api import records, tree, export, mapping, share_link, transfer, category, openlist, wechat, share_page, tmdb, media, xianyu, media_requests, quark_smart_transfer, rate_limit_admin
from backend.api import config as config_api
from backend.common.rate_limiter import RateLimitMiddleware, rate_limiter

# ✅ 使用统一的日志配置（支持环境变量控制）
from backend.common.logger import setup_logging
logger = setup_logging()

# 全局变量
db_engine = None
monitor_service = None
config = None
app_config = None  # 全局配置，用于其他模块访问


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db_engine, monitor_service, config, app_config
    
    # 启动时
    logger.info("🚀 启动文件监控硬链接系统...")
    
    # ✅ 预加载配置到缓存（提升后续请求性能）
    from backend.common.config_cache import ConfigCache
    from backend.common.thread_pool import get_executor
    
    ConfigCache.load_main_config()
    ConfigCache.load_cat_config()
    logger.info("✅ 配置缓存已预加载")
    
    # 初始化全局线程池
    get_executor()
    
    # 加载配置（兼容现有代码）
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    if not os.path.isabs(config_path):
        # 如果是相对路径，转换为绝对路径
        base_dir = Path(__file__).parent.parent
        config_path = str(base_dir / config_path)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        app_config = config  # 保存全局配置
    
    # 初始化数据库（MySQL硬编码配置）
    db_engine = init_database()
    logger.info("✅ 数据库初始化完成: MySQL (101.35.224.59:3306/file_link_monitor_v2)")
    
    # 启动监控服务
    monitor_service = MonitorService(config, db_engine)
    monitor_service.start()
    logger.info("✅ 监控服务已启动")
    
    # 初始化企业微信功能
    wechat_service = None
    try:
        wechat_service = wechat.init_wechat(config, db_engine)
    except Exception as e:
        logger.warning(f"⚠️ 企业微信功能初始化失败: {e}")
    
    # 启动闲鱼定时任务调度器
    try:
        from backend.services.xianyu_scheduler import get_scheduler
        scheduler = get_scheduler(wechat_service=wechat_service)
        await scheduler.start()
        logger.info("✅ 闲鱼定时任务调度器已启动（已配置微信通知）")
    except Exception as e:
        logger.warning(f"⚠️ 闲鱼调度器启动失败: {e}")
    
    # 启动TMDB剧集更新检查器
    try:
        from backend.services.tmdb_scheduler import init_checker
        tmdb_checker = init_checker(wechat_service)
        await tmdb_checker.start()
        logger.info("✅ TMDB剧集更新检查器已启动")
    except Exception as e:
        logger.warning(f"⚠️ TMDB检查器启动失败: {e}")
    
    # 启动分享链接检查器
    try:
        from backend.services.share_link_checker import init_checker as init_link_checker
        # 从配置读取检查间隔（小时），默认24小时
        share_link_config = config.get('share_link_checker', {})
        check_interval = share_link_config.get('check_interval_hours', 24)
        enabled = share_link_config.get('enabled', True)
        
        if enabled:
            link_checker = init_link_checker(wechat_service, check_interval)
            await link_checker.start()
            logger.info(f"✅ 分享链接检查器已启动 (间隔: {check_interval}小时)")
        else:
            logger.info("⏸️  分享链接检查器已禁用")
    except Exception as e:
        logger.warning(f"⚠️ 分享链接检查器启动失败: {e}")
    
    yield
    
    # 关闭时
    logger.info("⏹ 停止服务...")
    if monitor_service:
        monitor_service.stop()
    
    # 停止闲鱼调度器
    try:
        from backend.services.xianyu_scheduler import get_scheduler
        scheduler = get_scheduler()
        await scheduler.stop()
        logger.info("✅ 闲鱼调度器已停止")
    except:
        pass
    
    # 停止TMDB检查器
    try:
        from backend.services.tmdb_scheduler import get_checker
        tmdb_checker = get_checker()
        await tmdb_checker.stop()
        logger.info("✅ TMDB检查器已停止")
    except:
        pass
    
    # 停止分享链接检查器
    try:
        from backend.services.share_link_checker import get_checker as get_link_checker
        link_checker = get_link_checker()
        if link_checker:
            await link_checker.stop()
            logger.info("✅ 分享链接检查器已停止")
    except:
        pass
    
    # ✅ 关闭全局线程池
    from backend.common.thread_pool import shutdown_executor
    shutdown_executor()
    
    logger.info("👋 系统已关闭")


# 创建应用
app = FastAPI(
    title="文件监控硬链接系统",
    description="监控目录文件变化，自动创建硬链接",
    version="1.0.0",
    lifespan=lifespan
)

# 注册API路由
app.include_router(tree.router, prefix="/api", tags=["目录树"])
app.include_router(records.router, prefix="/api", tags=["记录"])
app.include_router(export.router, prefix="/api", tags=["导出"])
app.include_router(mapping.router, prefix="/api", tags=["映射管理"])
app.include_router(share_link.router, prefix="/api", tags=["分享链接"])
app.include_router(transfer.router, prefix="/api", tags=["网盘转存"])
app.include_router(category.router, prefix="/api", tags=["分类管理"])
app.include_router(openlist.router, prefix="/api", tags=["OpenList"])
app.include_router(wechat.router, prefix="/api", tags=["企业微信"])
app.include_router(quark_smart_transfer.router, prefix="/api", tags=["夸克智能转存"])
app.include_router(share_page.router, tags=["短链接分享"])
app.include_router(tmdb.router, prefix="/api", tags=["TMDb搜索"])
app.include_router(media.router, prefix="/api", tags=["媒体管理"])
app.include_router(xianyu.router, prefix="/api", tags=["闲鱼管家"])
app.include_router(media_requests.router, prefix="/api", tags=["资源请求"])
app.include_router(config_api.router, prefix="/api", tags=["配置管理"])
app.include_router(rate_limit_admin.router, prefix="/api", tags=["限流管理"])

# ✅ 添加中间件（注意顺序：先添加的后执行）
# 1. 限流中间件（最先执行，过滤恶意请求）
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

# 2. Gzip压缩中间件（最后执行，压缩响应）
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 静态文件
frontend_path = Path(__file__).parent.parent / "frontend-vue" / "dist"
# 挂载静态资源（CSS/JS等）- 使用长缓存（1年）
app.mount("/assets", CachedStaticFiles(directory=str(frontend_path / "assets"), max_age=31536000), name="assets")

# 挂载上传文件目录 - 使用中等缓存（7天）
uploads_path = Path(__file__).parent.parent / "uploads"
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", CachedStaticFiles(directory=str(uploads_path), max_age=604800), name="uploads")

# 挂载SVG文件目录（网盘Logo等）- 使用长缓存（1年）
svg_path = frontend_path / "svg"
if svg_path.exists():
    app.mount("/svg", CachedStaticFiles(directory=str(svg_path), max_age=31536000), name="svg")
    logger.info(f"✅ SVG目录已挂载: {svg_path}")
else:
    logger.warning(f"⚠️ SVG目录不存在: {svg_path}")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "file-link-monitor"}


@app.get("/api/config")
async def get_config():
    """获取配置"""
    monitors = config.get('monitors', [])
    notification = config.get('notification', {})
    taosync = config.get('taosync', {})
    pansou = config.get('pansou', {})
    openlist = config.get('openlist', {})
    wechat = config.get('wechat', {})
    
    if monitors:
        # 提取第一个监控配置
        monitor = monitors[0]
        return {
            "success": True,
            "data": {
                # 监控配置
                "source_dir": monitor.get('source', ''),
                "targets": [{'path': t.get('path', ''), 'name': t.get('name', '')} for t in monitor.get('targets', [])],
                "enabled": monitor.get('enabled', True),
                "obfuscate_enabled": monitor.get('obfuscate_enabled', True),
                "template_files_path": monitor.get('template_files_path', ''),
                "exclude_patterns": monitor.get('exclude_patterns', []),
                "scan_interval": 60,  # 固定值
                
                # 通知配置
                "notification_enabled": notification.get('enabled', False),
                "serverchan_url": notification.get('serverchan_url', ''),
                "serverchan_sendkey": notification.get('serverchan_sendkey', ''),
                
                # TaoSync配置
                "taosync_enabled": taosync.get('enabled', False),
                "taosync_url": taosync.get('url', ''),
                "taosync_username": taosync.get('username', ''),
                "taosync_password": taosync.get('password', ''),
                "taosync_job_id": taosync.get('job_id', 1),
                "taosync_check_interval": taosync.get('check_interval', 60),
                
                # 盘搜配置
                "pansou_enabled": pansou.get('enabled', False),
                "pansou_url": pansou.get('url', ''),
                "pansou_token": pansou.get('token', ''),
                "pansou_cloud_types": pansou.get('cloud_types', ['baidu', 'quark', 'xunlei']),
                
                # OpenList配置
                "openlist_url": openlist.get('url', ''),
                "openlist_token": openlist.get('token', ''),
                "openlist_path_prefix": openlist.get('path_prefix', ''),
                
                # 企业微信配置
                "wechat_enabled": wechat.get('enabled', False),
                "wechat_corp_id": wechat.get('corp_id', ''),
                "wechat_agent_id": wechat.get('agent_id', ''),
                "wechat_secret": wechat.get('secret', ''),
                "wechat_token": wechat.get('token', ''),
                "wechat_encoding_aes_key": wechat.get('encoding_aes_key', ''),
                "wechat_callback_url": wechat.get('callback_url', ''),
                "wechat_proxy_enabled": wechat.get('proxy', {}).get('enabled', False),
                "wechat_proxy_http": wechat.get('proxy', {}).get('http', ''),
                "wechat_proxy_https": wechat.get('proxy', {}).get('https', '')
            }
        }
    
    return {
        "success": True,
        "data": {
            "source_dir": '',
            "targets": [],
            "enabled": True,
            "obfuscate_enabled": True,
            "template_files_path": '',
            "exclude_patterns": ['*.tmp', '*.part', '.DS_Store'],
            "scan_interval": 60,
            "notification_enabled": False,
            "serverchan_url": '',
            "serverchan_sendkey": '',
            "taosync_enabled": False,
            "taosync_url": '',
            "taosync_username": '',
            "taosync_password": '',
            "taosync_job_id": 1,
            "taosync_check_interval": 60,
            "pansou_enabled": False,
            "pansou_url": '',
            "pansou_token": '',
            "pansou_cloud_types": ['baidu', 'quark', 'xunlei'],
            "openlist_url": '',
            "openlist_token": '',
            "openlist_path_prefix": '',
            "wechat_enabled": False,
            "wechat_corp_id": '',
            "wechat_agent_id": '',
            "wechat_secret": '',
            "wechat_token": '',
            "wechat_encoding_aes_key": '',
            "wechat_callback_url": '',
            "wechat_proxy_enabled": False,
            "wechat_proxy_http": '',
            "wechat_proxy_https": ''
        }
    }


@app.post("/api/config")
async def update_config(request: dict):
    """更新配置"""
    try:
        import yaml
        
        # 读取现有配置
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        if not os.path.isabs(config_path):
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / config_path
        
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
        
        # 更新监控配置
        targets = request.get('targets', [])
        # 处理targets，如果是字符串列表则转为对象列表
        formatted_targets = []
        for i, t in enumerate(targets):
            if isinstance(t, dict):
                formatted_targets.append({
                    'path': t.get('path', ''),
                    'name': t.get('name', f'目标{i+1}')
                })
            else:
                # 兼容旧格式（纯字符串）
                formatted_targets.append({
                    'path': t,
                    'name': f'目标{i+1}'
                })
        
        new_monitor = {
            'source': request.get('source_dir', ''),
            'targets': formatted_targets,
            'enabled': request.get('enabled', True),
            'obfuscate_enabled': request.get('obfuscate_enabled', True),
            'template_files_path': request.get('template_files_path', ''),
            'exclude_patterns': request.get('exclude_patterns', ['*.tmp', '*.part', '.DS_Store'])
        }
        
        if 'monitors' not in full_config:
            full_config['monitors'] = []
        
        if full_config['monitors']:
            full_config['monitors'][0] = new_monitor
        else:
            full_config['monitors'].append(new_monitor)
        
        # 更新通知配置
        full_config['notification'] = {
            'enabled': request.get('notification_enabled', False),
            'serverchan_url': request.get('serverchan_url', ''),
            'serverchan_sendkey': request.get('serverchan_sendkey', '')
        }
        
        # 更新TaoSync配置
        full_config['taosync'] = {
            'enabled': request.get('taosync_enabled', False),
            'url': request.get('taosync_url', ''),
            'username': request.get('taosync_username', ''),
            'password': request.get('taosync_password', ''),
            'job_id': request.get('taosync_job_id', 1),
            'check_interval': request.get('taosync_check_interval', 60)
        }
        
        # 更新盘搜配置
        full_config['pansou'] = {
            'enabled': request.get('pansou_enabled', False),
            'url': request.get('pansou_url', ''),
            'token': request.get('pansou_token', ''),
            'cloud_types': request.get('pansou_cloud_types', ['baidu', 'quark', 'xunlei'])
        }
        
        # 更新OpenList配置
        full_config['openlist'] = {
            'url': request.get('openlist_url', ''),
            'token': request.get('openlist_token', ''),
            'path_prefix': request.get('openlist_path_prefix', '')
        }
        
        # 更新企业微信配置
        full_config['wechat'] = {
            'enabled': request.get('wechat_enabled', False),
            'corp_id': request.get('wechat_corp_id', ''),
            'agent_id': request.get('wechat_agent_id', ''),
            'secret': request.get('wechat_secret', ''),
            'token': request.get('wechat_token', ''),
            'encoding_aes_key': request.get('wechat_encoding_aes_key', ''),
            'callback_url': request.get('wechat_callback_url', ''),
            'proxy': {
                'enabled': request.get('wechat_proxy_enabled', False),
                'http': request.get('wechat_proxy_http', ''),
                'https': request.get('wechat_proxy_https', '')
            }
        }
        
        # 保存配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(full_config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"✅ 配置已保存: {config_path}")
        
        # 自动重载配置
        global config, monitor_service
        config = full_config
        
        # 停止并重启监控服务
        if monitor_service:
            monitor_service.stop()
            logger.info("⏸️  已停止旧的监控服务")
        
        from backend.monitor import MonitorService
        monitor_service = MonitorService(config, db_engine)
        monitor_service.start()
        logger.info("✅ 监控服务已自动重启")
        
        return {
            "success": True,
            "message": "配置已保存并自动重载，无需重启服务"
        }
        
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return {
            "success": False,
            "message": f"保存失败: {str(e)}"
        }


@app.post("/api/reload-config")
async def reload_config():
    """重新加载配置（热重载）"""
    try:
        global config, monitor_service
        
        # 重新加载配置文件
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        if not os.path.isabs(config_path):
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / config_path
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        logger.info("✅ 配置文件已重新加载")
        
        # 停止旧的监控服务
        if monitor_service:
            monitor_service.stop()
            logger.info("⏸️  已停止旧的监控服务")
        
        # 重新初始化监控服务
        from backend.monitor import MonitorService
        monitor_service = MonitorService(config, db_engine)
        monitor_service.start()
        logger.info("✅ 监控服务已重启")
        
        return {
            "success": True,
            "message": "配置已重新加载，监控服务已重启"
        }
        
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"重新加载失败: {str(e)}"
        }


@app.post("/api/sync-all")
async def sync_all():
    """全量同步所有文件"""
    try:
        result = monitor_service.sync_all()
        return result
    except Exception as e:
        logger.error(f"全量同步失败: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/trigger-taosync")
async def trigger_taosync():
    """手动触发TaoSync同步"""
    try:
        if not monitor_service or not monitor_service.handlers:
            return {"success": False, "message": "监控服务未启动"}
        
        triggered = False
        for handler in monitor_service.handlers:
            if hasattr(handler, 'taosync_queue') and handler.taosync_queue:
                logger.info("手动触发TaoSync同步")
                success, reason = handler.taosync_queue.trigger_now(force=True)
                triggered = True
                if success:
                    return {"success": True, "message": "TaoSync同步已触发"}
                else:
                    return {"success": False, "message": f"触发失败: {reason}"}
        
        if not triggered:
            return {"success": False, "message": "TaoSync未配置或未启用"}
    except Exception as e:
        logger.error(f"触发TaoSync失败: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/batch-link-templates")
async def batch_link_templates():
    """批量补充模板文件到所有剧集/电影目录"""
    try:
        if not monitor_service or not monitor_service.handlers:
            return {"success": False, "message": "监控服务未启动"}
        
        result = monitor_service.batch_link_templates()
        return result
    except Exception as e:
        logger.error(f"批量补充模板文件失败: {e}")
        return {"success": False, "message": str(e)}


# 根路径
@app.get("/")
async def root():
    """返回前端首页"""
    return FileResponse(str(frontend_path / "index.html"))

# 前端路由 - 明确指定所有前端页面路径
frontend_routes = [
    "/media",
    "/mappings",
    "/records",
    "/share-links",
    "/media-requests",
    "/config",
    "/xianyu/products",
    "/xianyu/create-product",
    "/xianyu/auto-workflow",
    "/xianyu/schedule-tasks"
]

for route in frontend_routes:
    # 为每个前端路由创建一个处理函数
    def make_handler(r=route):
        async def handler():
            return FileResponse(str(frontend_path / "index.html"))
        return handler
    
    app.get(route)(make_handler())


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
