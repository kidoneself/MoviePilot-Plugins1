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
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CustomNameMapping(Base):
    """自定义名称映射表（支持双网盘）"""
    __tablename__ = "custom_name_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_name = Column(String(191), nullable=False, unique=True)
    
    # 双网盘显示名
    quark_name = Column(String(500))
    baidu_name = Column(String(500))
    
    # 网盘链接
    quark_link = Column(String(1000))
    baidu_link = Column(String(1000))
    
    enabled = Column(Boolean, default=True)
    note = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_original_name', 'original_name'),
    )


def init_database(db_config: dict = None):
    """
    初始化数据库
    使用MySQL（硬编码配置）
    """
    # MySQL配置（硬编码）
    db_url = 'mysql+pymysql://root:MyStrongPass123@10.10.10.17:3306/file_link_monitor_v2?charset=utf8mb4'
    
    engine = create_engine(
        db_url, 
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()
