"""
闲鱼管家数据库模型
复用 Java 项目的表结构
"""
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, DateTime
from sqlalchemy.sql import func
from backend.models import Base


class GoofishProduct(Base):
    """闲鱼商品表"""
    __tablename__ = 'goofish_product'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, unique=True, nullable=False, index=True, comment='闲鱼商品ID')
    title = Column(String(500), comment='商品标题')
    outer_id = Column(String(100), comment='外部ID')
    price = Column(BigInteger, comment='价格（分）')
    original_price = Column(BigInteger, comment='原价（分）')
    stock = Column(Integer, comment='库存')
    sold = Column(Integer, comment='已售')
    product_status = Column(Integer, comment='商品状态')
    item_biz_type = Column(Integer, comment='商品业务类型')
    sp_biz_type = Column(Integer, comment='SP业务类型')
    channel_cat_id = Column(String(100), comment='类目ID')
    district_id = Column(Integer, comment='地区ID')
    stuff_status = Column(Integer, comment='成色')
    express_fee = Column(BigInteger, comment='运费（分）')
    spec_type = Column(Integer, comment='规格类型')
    source = Column(Integer, comment='来源')
    specify_publish_time = Column(BigInteger, comment='指定发布时间')
    online_time = Column(BigInteger, comment='上架时间')
    offline_time = Column(BigInteger, comment='下架时间')
    sold_time = Column(BigInteger, comment='售出时间')
    update_time_remote = Column(BigInteger, comment='远程更新时间')
    create_time_remote = Column(BigInteger, comment='远程创建时间')
    
    # 本地字段
    is_selected = Column(Boolean, default=False, comment='是否选中')
    sync_time = Column(DateTime, server_default=func.now(), comment='同步时间')
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 关联媒体库（扩展字段）
    media_id = Column(BigInteger, nullable=True, index=True, comment='关联媒体库ID')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'title': self.title,
            'outer_id': self.outer_id,
            'price': self.price,
            'original_price': self.original_price,
            'stock': self.stock,
            'sold': self.sold,
            'product_status': self.product_status,
            'item_biz_type': self.item_biz_type,
            'sp_biz_type': self.sp_biz_type,
            'channel_cat_id': self.channel_cat_id,
            'district_id': self.district_id,
            'stuff_status': self.stuff_status,
            'express_fee': self.express_fee,
            'spec_type': self.spec_type,
            'source': self.source,
            'specify_publish_time': self.specify_publish_time,
            'online_time': self.online_time,
            'offline_time': self.offline_time,
            'sold_time': self.sold_time,
            'update_time_remote': self.update_time_remote,
            'create_time_remote': self.create_time_remote,
            'is_selected': self.is_selected,
            'sync_time': self.sync_time.isoformat() if self.sync_time else None,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'media_id': self.media_id,
        }


class GoofishConfig(Base):
    """闲鱼配置表"""
    __tablename__ = 'goofish_config'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True, comment='配置键')
    config_value = Column(Text, comment='配置值')
    config_type = Column(String(50), comment='配置类型')
    description = Column(String(500), comment='描述')
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }


class GoofishScheduleTask(Base):
    """闲鱼定时任务表"""
    __tablename__ = 'goofish_schedule_task'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_type = Column(String(20), nullable=False, comment='任务类型: publish/downshelf')
    product_ids = Column(Text, comment='商品ID列表（JSON）')
    product_titles = Column(Text, comment='商品标题列表（JSON）')
    execute_time = Column(DateTime, nullable=False, comment='执行时间')
    repeat_daily = Column(Boolean, default=False, comment='是否每日重复')
    status = Column(String(20), default='PENDING', comment='状态: PENDING/COMPLETED/FAILED/CANCELLED')
    execute_result = Column(Text, comment='执行结果')
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    last_execute_time = Column(DateTime, comment='最后执行时间')
    
    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'task_type': self.task_type,
            'product_ids': json.loads(self.product_ids) if self.product_ids else [],
            'product_titles': json.loads(self.product_titles) if self.product_titles else [],
            'execute_time': self.execute_time.isoformat() if self.execute_time else None,
            'repeat_daily': self.repeat_daily,
            'status': self.status,
            'execute_result': self.execute_result,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'last_execute_time': self.last_execute_time.isoformat() if self.last_execute_time else None,
        }

