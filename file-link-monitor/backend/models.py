from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, create_engine
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


def init_database(db_path: str):
    """初始化数据库"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()
