import os
import yaml
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from backend.models import init_database
from backend.monitor import MonitorService
from backend.api import records, tree, export, mapping, share_link

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
db_engine = None
monitor_service = None
config = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db_engine, monitor_service, config
    
    # 启动时
    logger.info("🚀 启动文件监控硬链接系统...")
    
    # 加载配置
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    if not os.path.isabs(config_path):
        # 如果是相对路径，转换为绝对路径
        base_dir = Path(__file__).parent.parent
        config_path = str(base_dir / config_path)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化数据库（MySQL硬编码配置）
    db_engine = init_database()
    logger.info("✅ 数据库初始化完成: MySQL (10.10.10.17:3306/file_link_monitor_v2)")
    
    # 启动监控服务
    monitor_service = MonitorService(config, db_engine)
    monitor_service.start()
    logger.info("✅ 监控服务已启动")
    
    yield
    
    # 关闭时
    logger.info("⏹ 停止监控服务...")
    if monitor_service:
        monitor_service.stop()
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

# 静态文件
frontend_path = Path(__file__).parent.parent / "frontend"
# 挂载静态资源（CSS/JS等）
app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")


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
                "taosync_check_interval": taosync.get('check_interval', 60)
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
            "taosync_check_interval": 60
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


# 通配符路由放在最后，作为fallback处理Vue Router
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    提供前端页面，支持Vue Router
    所有非API请求返回index.html
    """
    return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
