"""
定时任务 CRUD 操作
"""

import uuid
from datetime import datetime
from sqlmodel import Session, select, func
from app.models.base import get_datetime_china
from app.models.scheduled_task import (
    ScheduledTask,
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    TaskExecutionLog,
)


def create_task(*, session: Session, task_in: ScheduledTaskCreate) -> ScheduledTask:
    """创建定时任务"""
    db_task = ScheduledTask.model_validate(task_in)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def get_task(*, session: Session, task_id: uuid.UUID) -> ScheduledTask | None:
    """获取单个定时任务"""
    return session.get(ScheduledTask, task_id)


def get_tasks(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    project_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
) -> list[ScheduledTask]:
    """获取定时任务列表"""
    statement = select(ScheduledTask)
    
    if project_id:
        statement = statement.where(ScheduledTask.project_id == project_id)
    if is_enabled is not None:
        statement = statement.where(ScheduledTask.is_enabled == is_enabled)
    
    statement = statement.order_by(ScheduledTask.created_at.desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_tasks(
    *,
    session: Session,
    project_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
) -> int:
    """统计定时任务数量"""
    statement = select(func.count()).select_from(ScheduledTask)
    
    if project_id:
        statement = statement.where(ScheduledTask.project_id == project_id)
    if is_enabled is not None:
        statement = statement.where(ScheduledTask.is_enabled == is_enabled)
    
    return session.exec(statement).one()


def update_task(
    *,
    session: Session,
    db_task: ScheduledTask,
    task_in: ScheduledTaskUpdate,
) -> ScheduledTask:
    """更新定时任务"""
    task_data = task_in.model_dump(exclude_unset=True)
    db_task.sqlmodel_update(task_data)
    db_task.updated_at = get_datetime_china()
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def delete_task(*, session: Session, db_task: ScheduledTask) -> None:
    """删除定时任务"""
    from app.models.scheduled_task import TaskExecutionLog
    # 先删除所有关联的执行日志，避免外键约束错误
    session.query(TaskExecutionLog).filter(TaskExecutionLog.task_id == db_task.id).delete(synchronize_session=False)
    session.delete(db_task)
    session.commit()


def update_task_run_times(
    *,
    session: Session,
    db_task: ScheduledTask,
    last_run_at: datetime | None = None,
    next_run_at: datetime | None = None,
) -> ScheduledTask:
    """更新任务执行时间"""
    if last_run_at:
        db_task.last_run_at = last_run_at
    if next_run_at:
        db_task.next_run_at = next_run_at
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def get_enabled_tasks(*, session: Session) -> list[ScheduledTask]:
    """获取所有启用的任务"""
    statement = select(ScheduledTask).where(ScheduledTask.is_enabled == True)
    return list(session.exec(statement).all())


def create_task_log(
    *,
    session: Session,
    task_id: uuid.UUID,
    execution_id: uuid.UUID | None = None,
    status: str = "pending",
) -> TaskExecutionLog:
    """创建任务执行日志"""
    db_log = TaskExecutionLog(
        task_id=task_id,
        execution_id=execution_id,
        status=status,
    )
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


def get_task_logs(
    *,
    session: Session,
    task_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TaskExecutionLog]:
    """获取任务执行日志列表"""
    statement = select(TaskExecutionLog)
    
    if task_id:
        statement = statement.where(TaskExecutionLog.task_id == task_id)
    
    statement = statement.order_by(TaskExecutionLog.created_at.desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_task_logs(
    *,
    session: Session,
    task_id: uuid.UUID | None = None,
) -> int:
    """统计任务执行日志数量"""
    statement = select(func.count()).select_from(TaskExecutionLog)
    
    if task_id:
        statement = statement.where(TaskExecutionLog.task_id == task_id)
    
    return session.exec(statement).one()


def update_task_log(
    *,
    session: Session,
    db_log: TaskExecutionLog,
    status: str | None = None,
    execution_id: uuid.UUID | None = None,
    error_message: str | None = None,
    finished_at: datetime | None = None,
    retry_count: int | None = None,
    attempt_number: int | None = None,
) -> TaskExecutionLog:
    """更新任务执行日志"""
    # 关键修复：如果会话处于 rollback 状态，先执行 rollback
    try:
        session.commit()
    except Exception:
        session.rollback()
    
    if status:
        db_log.status = status
    if execution_id:
        db_log.execution_id = execution_id
    if error_message:
        db_log.error_message = error_message
    if finished_at:
        db_log.finished_at = finished_at
    if retry_count is not None:
        db_log.retry_count = retry_count
    if attempt_number is not None:
        db_log.attempt_number = attempt_number
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log
