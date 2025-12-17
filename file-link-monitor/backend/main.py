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
from backend.api import tree, records, export

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
    
    # 初始化数据库
    db_path = config['database']['path']
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db_engine = init_database(db_path)
    logger.info(f"✅ 数据库初始化完成: {db_path}")
    
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

# 静态文件
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
async def root():
    """首页"""
    return FileResponse(str(frontend_path / "index.html"))


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "file-link-monitor"}


@app.get("/api/config")
async def get_config():
    """获取配置"""
    return {
        "success": True,
        "data": {
            "monitors": config.get('monitors', [])
        }
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


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
