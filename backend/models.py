from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, BigInteger, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class MonitorConfig(Base):
    """监控配置表"""
    __tablename__ = "monitor_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_path = Column(String(500), nullable=False)
    target_paths = Column(Text, nullable=False)  # JSON字符串
    enabled = Column(Boolean, default=True)
    exclude_patterns = Column(Text)  # JSON字符串
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class LinkRecord(Base):
    """硬链接记录表（支持双网盘）"""
    __tablename__ = "link_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(768), nullable=False, unique=True)
    original_name = Column(String(191))
    file_size = Column(BigInteger)
    
    # 网盘1（夸克）
    quark_target_file = Column(String(1000))
    quark_synced_at = Column(DateTime)
    
    # 网盘2（百度）
    baidu_target_file = Column(String(1000))
    baidu_synced_at = Column(DateTime)
    
    # 网盘3（迅雷）
    xunlei_target_file = Column(String(1000))
    xunlei_synced_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CustomNameMapping(Base):
    """自定义名称映射表（支持双网盘）"""
    __tablename__ = "custom_name_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_name = Column(String(191), nullable=False, unique=True)
    category = Column(String(100), comment='二级分类：电影/国产电影')
    
    # 三网盘显示名
    quark_name = Column(String(500))
    baidu_name = Column(String(500))
    xunlei_name = Column(String(500))
    
    # 网盘链接
    quark_link = Column(String(1000))
    baidu_link = Column(String(1000))
    xunlei_link = Column(String(1000))
    
    enabled = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False, comment='是否完结')
    note = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_original_name', 'original_name'),
    )


class PanCookie(Base):
    """网盘Cookie管理表"""
    __tablename__ = 'pan_cookies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pan_type = Column(String(20), nullable=False, unique=True, comment='网盘类型: baidu/quark/xunlei')
    cookie = Column(Text, nullable=False, comment='Cookie字符串')
    is_active = Column(Boolean, default=True, comment='是否启用')
    last_check_time = Column(DateTime, comment='最后检查时间')
    check_status = Column(String(50), comment='检查状态: valid/invalid/unknown')
    check_error = Column(Text, comment='检查错误信息')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_database(db_config: dict = None):
    """
    初始化数据库
    支持MySQL和SQLite，从配置文件读取
    """
    if not db_config:
        db_config = {}
    
    db_type = db_config.get('type', 'mysql')
    
    if db_type == 'mysql':
        # MySQL配置
        mysql_config = db_config.get('mysql', {})
        host = mysql_config.get('host', '10.10.10.17')
        port = mysql_config.get('port', 3306)
        user = mysql_config.get('user', 'root')
        password = mysql_config.get('password', 'MyStrongPass123')
        database = mysql_config.get('database', 'file_link_monitor_v2')
        charset = mysql_config.get('charset', 'utf8mb4')
        
        db_url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}'
        
        engine = create_engine(
            db_url, 
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True
        )
    else:
        # SQLite配置
        sqlite_config = db_config.get('sqlite', {})
        db_path = sqlite_config.get('path', './data/database.db')
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db_url = f'sqlite:///{db_path}'
        engine = create_engine(db_url, echo=False)
    
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()


def get_db():
    """FastAPI依赖注入：获取数据库会话"""
    from backend.main import db_engine
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()
