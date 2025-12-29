#!/usr/bin/env python3
"""
清理数据库中有问题的定时任务
用于修复JSON格式错误的任务
"""
import sys
import json
import yaml
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models import get_session, init_database
from backend.models.xianyu import GoofishScheduleTask

def get_db_engine():
    """初始化数据库引擎"""
    # 读取配置文件
    config_path = Path(__file__).parent.parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化数据库（传入完整的数据库配置）
    db_config = config.get('database', {})
    engine = init_database(db_config)
    return engine

def cleanup_tasks():
    """清理有问题的定时任务"""
    engine = get_db_engine()
    session = get_session(engine)
    
    try:
        deleted_count = 0
        error_tasks = []
        
        # 获取所有PENDING任务
        tasks = session.query(GoofishScheduleTask).filter_by(status='PENDING').all()
        
        print(f"找到 {len(tasks)} 个待执行任务，开始检查...")
        
        for task in tasks:
            has_error = False
            error_msg = []
            
            # 检查product_ids
            try:
                if task.product_ids:
                    json.loads(task.product_ids)
            except json.JSONDecodeError as e:
                has_error = True
                error_msg.append(f"product_ids JSON错误: {e}")
            
            # 检查product_titles
            try:
                if task.product_titles:
                    json.loads(task.product_titles)
            except json.JSONDecodeError as e:
                has_error = True
                error_msg.append(f"product_titles JSON错误: {e}")
            
            if has_error:
                print(f"\n发现有问题的任务:")
                print(f"  任务ID: {task.id}")
                print(f"  任务类型: {task.task_type}")
                print(f"  执行时间: {task.execute_time}")
                print(f"  错误信息: {', '.join(error_msg)}")
                print(f"  product_ids: {task.product_ids[:100] if task.product_ids else 'None'}...")
                print(f"  product_titles: {task.product_titles[:100] if task.product_titles else 'None'}...")
                
                error_tasks.append({
                    'id': task.id,
                    'task_type': task.task_type,
                    'errors': error_msg
                })
                
                # 删除该任务
                session.delete(task)
                deleted_count += 1
        
        if deleted_count > 0:
            confirm = input(f"\n是否确认删除这 {deleted_count} 个有问题的任务? (y/n): ")
            if confirm.lower() == 'y':
                session.commit()
                print(f"\n✅ 已删除 {deleted_count} 个有问题的任务")
            else:
                session.rollback()
                print("\n❌ 已取消删除操作")
        else:
            print("\n✅ 没有发现有问题的任务")
        
        return {
            'deleted_count': deleted_count,
            'error_tasks': error_tasks
        }
        
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def cleanup_all():
    """清理所有待执行和失败的任务（谨慎使用）"""
    engine = get_db_engine()
    session = get_session(engine)
    
    try:
        # 统计数量
        pending_count = session.query(GoofishScheduleTask).filter_by(status='PENDING').count()
        failed_count = session.query(GoofishScheduleTask).filter_by(status='FAILED').count()
        total = pending_count + failed_count
        
        if total == 0:
            print("没有需要清理的任务")
            return
        
        print(f"\n找到以下任务:")
        print(f"  待执行 (PENDING): {pending_count} 个")
        print(f"  失败 (FAILED): {failed_count} 个")
        print(f"  总计: {total} 个")
        
        confirm = input(f"\n⚠️  是否确认删除所有这些任务? (y/n): ")
        if confirm.lower() != 'y':
            print("❌ 已取消删除操作")
            return
        
        # 删除所有PENDING和FAILED任务
        deleted = session.query(GoofishScheduleTask).filter(
            GoofishScheduleTask.status.in_(['PENDING', 'FAILED'])
        ).delete(synchronize_session=False)
        
        session.commit()
        print(f"\n✅ 已删除 {deleted} 个任务")
        
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='清理定时任务')
    parser.add_argument('--all', action='store_true', help='清理所有待执行和失败的任务（谨慎使用）')
    args = parser.parse_args()
    
    if args.all:
        print("模式: 清理所有任务")
        cleanup_all()
    else:
        print("模式: 只清理有问题的任务")
        cleanup_tasks()

