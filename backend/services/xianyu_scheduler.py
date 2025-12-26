"""
闲鱼商品定时任务调度器
定时执行上架/下架操作
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
import json

from sqlalchemy import and_
from backend.models import get_session
from backend.models.xianyu import GoofishScheduleTask

def _get_session():
    """获取数据库会话"""
    from backend.main import db_engine
    return get_session(db_engine)
from backend.utils.xianyu_api import (
    GoofishSDK, GoofishConfig as SDKConfig,
    PublishProductRequest, DownShelfProductRequest, ProductListRequest
)
from backend.models.xianyu import GoofishProduct

logger = logging.getLogger(__name__)


class XianyuScheduler:
    """闲鱼定时任务调度器"""
    
    def __init__(self):
        self.running = False
        self.sdk: Optional[GoofishSDK] = None
    
    def _init_sdk(self):
        """初始化SDK"""
        if self.sdk is not None:
            return
        
        session = _get_session()
        try:
            from backend.models.xianyu import GoofishConfig as DBConfig
            
            app_key_cfg = session.query(DBConfig).filter_by(config_key='goofish.app_key').first()
            app_secret_cfg = session.query(DBConfig).filter_by(config_key='goofish.app_secret').first()
            
            if not app_key_cfg or not app_secret_cfg:
                logger.warning("闲鱼配置未设置，跳过定时任务")
                return
            
            config = SDKConfig(
                app_key=app_key_cfg.config_value,
                app_secret=app_secret_cfg.config_value
            )
            self.sdk = GoofishSDK(config)
            logger.info("闲鱼SDK初始化成功")
        except Exception as e:
            logger.error(f"初始化闲鱼SDK失败: {e}")
        finally:
            session.close()
    
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        logger.info("闲鱼定时任务调度器启动")
        
        # 启动定时检查循环
        asyncio.create_task(self._check_loop())
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        if self.sdk:
            self.sdk.close()
            self.sdk = None
        logger.info("闲鱼定时任务调度器已停止")
    
    async def _check_loop(self):
        """定时检查循环"""
        while self.running:
            try:
                await self._check_and_execute_tasks()
            except Exception as e:
                logger.error(f"检查任务失败: {e}", exc_info=True)
            
            # 每分钟检查一次
            await asyncio.sleep(60)
    
    async def _check_and_execute_tasks(self):
        """检查并执行待执行的任务"""
        session = _get_session()
        try:
            now = datetime.now()
            
            # 查询待执行的任务（状态为PENDING，执行时间小于等于当前时间）
            tasks = session.query(GoofishScheduleTask).filter(
                and_(
                    GoofishScheduleTask.status == 'PENDING',
                    GoofishScheduleTask.execute_time <= now
                )
            ).all()
            
            if not tasks:
                return
            
            logger.info(f"找到 {len(tasks)} 个待执行任务")
            
            # 初始化SDK
            if not self.sdk:
                self._init_sdk()
            
            if not self.sdk:
                logger.warning("SDK未初始化，跳过任务执行")
                return
            
            # 执行任务
            for task in tasks:
                try:
                    await self._execute_task(task, session)
                except Exception as e:
                    logger.error(f"执行任务 {task.id} 失败: {e}", exc_info=True)
                    task.status = 'FAILED'
                    task.execute_result = str(e)
                    session.commit()
        
        finally:
            session.close()
    
    async def _sync_products_after_task(self, product_ids: List[int], session):
        """任务执行后同步商品状态"""
        try:
            # 构建请求，查询所有商品（不限时间范围）
            request = ProductListRequest(
                pageNo=1,
                pageSize=100  # 一次查询100个，足够覆盖大部分情况
            )
            
            # 查询商品列表
            response = self.sdk.product().list_product(request)
            
            synced_count = 0
            for item in response.list:
                product_id = item.get('product_id')
                if not product_id:
                    continue
                
                # 查找数据库记录
                db_product = session.query(GoofishProduct).filter_by(product_id=product_id).first()
                
                if db_product:
                    # 更新状态
                    old_status = db_product.product_status
                    new_status = item.get('product_status')
                    
                    db_product.product_status = new_status
                    db_product.stock = item.get('stock')
                    db_product.sold = item.get('sold')
                    db_product.online_time = item.get('online_time')
                    db_product.offline_time = item.get('offline_time')
                    db_product.sync_time = datetime.now()
                    
                    if old_status != new_status:
                        logger.info(f"商品状态已更新: {product_id} {old_status} -> {new_status}")
                    
                    synced_count += 1
            
            session.commit()
            logger.info(f"✅ 商品状态同步完成，更新了 {synced_count} 个商品")
            
        except Exception as e:
            logger.error(f"同步商品状态失败: {e}")
            raise
    
    async def _execute_task(self, task: GoofishScheduleTask, session):
        """执行单个任务"""
        logger.info(f"执行任务 {task.id}: {task.task_type}")
        
        try:
            # 解析商品ID列表
            product_ids = json.loads(task.product_ids) if task.product_ids else []
            
            if not product_ids:
                task.status = 'FAILED'
                task.execute_result = '商品ID列表为空'
                session.commit()
                return
            
            # 根据任务类型执行
            results = []
            
            for product_id in product_ids:
                try:
                    if task.task_type == 'publish':
                        # 上架
                        # 需要获取username，这里简化处理，使用默认配置
                        from backend.models.xianyu import GoofishConfig as DBConfig
                        username_cfg = session.query(DBConfig).filter_by(config_key='username1').first()
                        username = username_cfg.config_value if username_cfg else ''
                        
                        if not username:
                            results.append(f"商品 {product_id}: 失败 - 未配置用户名")
                            continue
                        
                        request = PublishProductRequest(
                            productId=product_id,
                            userName=[username]
                        )
                        self.sdk.product().publish_product(request)
                        results.append(f"商品 {product_id}: 上架成功")
                        
                    elif task.task_type == 'downshelf':
                        # 下架
                        request = DownShelfProductRequest(productId=product_id)
                        self.sdk.product().downshelf_product(request)
                        results.append(f"商品 {product_id}: 下架成功")
                    
                    else:
                        results.append(f"商品 {product_id}: 未知任务类型")
                
                except Exception as e:
                    logger.error(f"商品 {product_id} 执行失败: {e}")
                    results.append(f"商品 {product_id}: 失败 - {str(e)}")
            
            # 更新任务状态
            task.status = 'COMPLETED'
            task.execute_result = '\n'.join(results)
            task.last_execute_time = datetime.now()
            
            # 如果是每日重复任务，创建下一个任务
            if task.repeat_daily:
                next_task = GoofishScheduleTask(
                    task_type=task.task_type,
                    product_ids=task.product_ids,
                    product_titles=task.product_titles,
                    execute_time=task.execute_time + timedelta(days=1),
                    repeat_daily=True,
                    status='PENDING'
                )
                session.add(next_task)
            
            session.commit()
            logger.info(f"任务 {task.id} 执行完成")
            
            # 任务执行完成后，同步所有商品状态
            try:
                logger.info("定时任务完成，开始同步商品状态...")
                await self._sync_products_after_task(product_ids, session)
            except Exception as e:
                logger.error(f"同步商品状态失败: {e}", exc_info=True)
        
        except Exception as e:
            task.status = 'FAILED'
            task.execute_result = str(e)
            session.commit()
            raise


# 全局调度器实例
_scheduler_instance: Optional[XianyuScheduler] = None


def get_scheduler() -> XianyuScheduler:
    """获取调度器实例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = XianyuScheduler()
    return _scheduler_instance

