"""
定时任务 API 路由

支持功能：
- 任务 CRUD
- 任务启用/禁用
- 手动触发执行
- 执行日志查看

优化内容：
- 支持重试次数、重试间隔、超时配置
- 删除任务时清理执行锁
"""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.scheduled_task import (
    ScheduledTask,
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskPublic,
    ScheduledTasksPublic,
    TaskExecutionLogPublic,
    TaskExecutionLogsPublic,
    TriggerTaskRequest,
    EnableTaskResponse,
)
from app.models import Message
from app.crud.scheduled_task import (
    create_task,
    get_task,
    get_tasks,
    count_tasks,
    update_task,
    delete_task,
    get_task_logs,
    count_task_logs,
)
from app.services.scheduler_service import scheduler_service, cleanup_task_lock
from app.models.base import get_datetime_china


router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


@router.get("/", response_model=ScheduledTasksPublic)
def read_tasks(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    project_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
) -> Any:
    """获取定时任务列表"""
    tasks = get_tasks(
        session=session,
        skip=skip,
        limit=limit,
        project_id=project_id,
        is_enabled=is_enabled,
    )
    count = count_tasks(
        session=session,
        project_id=project_id,
        is_enabled=is_enabled,
    )
    return ScheduledTasksPublic(data=tasks, count=count)


@router.get("/{task_id}", response_model=ScheduledTaskPublic)
def read_task(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
) -> Any:
    """获取单个定时任务"""
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return task


@router.post("/", response_model=ScheduledTaskPublic)
def create_task_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_in: ScheduledTaskCreate,
) -> Any:
    """创建定时任务"""
    task = create_task(session=session, task_in=task_in)
    
    if task.is_enabled:
        try:
            next_run = scheduler_service.add_job(task)
            from app.crud.scheduled_task import update_task_run_times
            update_task_run_times(
                session=session,
                db_task=task,
                next_run_at=next_run,
            )
            session.refresh(task)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"任务调度配置错误: {str(e)}")
    
    return task


@router.put("/{task_id}", response_model=ScheduledTaskPublic)
def update_task_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
    task_in: ScheduledTaskUpdate,
) -> Any:
    """更新定时任务"""
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    task = update_task(session=session, db_task=task, task_in=task_in)
    
    scheduler_service.remove_job(task_id)
    
    if task.is_enabled:
        try:
            next_run = scheduler_service.add_job(task)
            from app.crud.scheduled_task import update_task_run_times
            update_task_run_times(
                session=session,
                db_task=task,
                next_run_at=next_run,
            )
            session.refresh(task)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"任务调度配置错误: {str(e)}")
    
    return task


@router.delete("/{task_id}", response_model=Message)
def delete_task_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
    force: bool = False,
) -> Any:
    """删除定时任务
    
    Args:
        force: 是否强制删除（即使任务正在运行）
    """
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    scheduler_service.remove_job(task_id)
    cleanup_task_lock(str(task_id))
    
    # delete_task 内部已处理关联执行日志的级联删除
    delete_task(session=session, db_task=task)
    return Message(message="删除成功")


@router.post("/{task_id}/enable", response_model=EnableTaskResponse)
def enable_task(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
) -> Any:
    """启用定时任务"""
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    task = update_task(session=session, db_task=task, task_in=ScheduledTaskUpdate(is_enabled=True))
    
    try:
        next_run = scheduler_service.add_job(task)
        from app.crud.scheduled_task import update_task_run_times
        update_task_run_times(
            session=session,
            db_task=task,
            next_run_at=next_run,
        )
        session.refresh(task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"任务调度配置错误: {str(e)}")
    
    return EnableTaskResponse(message="已启用", next_run_at=task.next_run_at)


@router.post("/{task_id}/disable", response_model=Message)
def disable_task(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
) -> Any:
    """禁用定时任务"""
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    task = update_task(session=session, db_task=task, task_in=ScheduledTaskUpdate(is_enabled=False))
    
    scheduler_service.remove_job(task_id)
    
    return Message(message="已禁用")


@router.post("/{task_id}/trigger", response_model=Message)
async def trigger_task(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
) -> Any:
    """立即触发任务"""
    from app.services.scheduler_service import run_scheduled_task
    
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    job_id = str(task_id)
    job = scheduler_service._scheduler.get_job(job_id)
    
    if job:
        scheduler_service.trigger_job(task_id)
    else:
        import asyncio
        await asyncio.to_thread(run_scheduled_task, str(task_id))
    
    return Message(message="已触发执行")


@router.get("/{task_id}/logs", response_model=TaskExecutionLogsPublic)
def read_task_logs(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """获取任务执行日志"""
    task = get_task(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    logs = get_task_logs(
        session=session,
        task_id=task_id,
        skip=skip,
        limit=limit,
    )
    count = count_task_logs(
        session=session,
        task_id=task_id,
    )
    return TaskExecutionLogsPublic(data=logs, count=count)


@router.get("/logs/all", response_model=TaskExecutionLogsPublic)
def read_all_logs(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """获取所有任务执行日志"""
    logs = get_task_logs(
        session=session,
        task_id=None,
        skip=skip,
        limit=limit,
    )
    count = count_task_logs(
        session=session,
        task_id=None,
    )
    return TaskExecutionLogsPublic(data=logs, count=count)
