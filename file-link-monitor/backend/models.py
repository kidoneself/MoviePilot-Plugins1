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
    """硬链接记录表"""
    __tablename__ = "link_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(1000), nullable=False)
    target_file = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    link_method = Column(String(20))  # 硬链接/复制
    status = Column(String(20))  # success/failed
    error_msg = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class CustomNameMapping(Base):
    """自定义名称映射表"""
    __tablename__ = "custom_name_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_name = Column(String(500), nullable=False, unique=True)  # 原名（唯一）
    custom_name = Column(String(500), nullable=False)  # 自定义名称
    enabled = Column(Boolean, default=True)  # 是否启用
    note = Column(String(500))  # 备注说明
    baidu_link = Column(String(1000))  # 百度网盘链接
    quark_link = Column(String(1000))  # 夸克网盘链接
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_original_name', 'original_name'),
    )


def init_database(db_path: str):
    """初始化数据库"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()
