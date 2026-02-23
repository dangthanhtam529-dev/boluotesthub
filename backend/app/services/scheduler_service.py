"""
定时任务调度器服务

使用 APScheduler 实现任务调度，支持：
- Cron 表达式触发
- 固定间隔触发
- 单次执行

优化内容：
- 重试机制：支持配置重试次数和间隔，指数退避
- 超时控制：任务级超时，超时后强制终止
- 执行锁：防止同一任务并发执行
- 详细日志：记录每次执行和重试的详细信息
"""

import json
import uuid
import asyncio
import logging
import threading
from datetime import datetime
from typing import Any
from concurrent.futures import TimeoutError as FuturesTimeoutError

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models.base import get_datetime_china
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.models.scheduled_task import (
    ScheduledTask,
    TriggerType,
    TaskExecutionLog,
    RETRY_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_INTERVAL,
    DEFAULT_TIMEOUT,
)
from app.models.execution import TestExecution, TestExecutionCreate
from app.crud.scheduled_task import (
    get_task,
    update_task_run_times,
    create_task_log,
    update_task_log,
)
from app.crud.execution import create_execution, update_execution
from app.crud.project import get_project
from app.services.apifox import apifox_service
from app.services.notification_trigger import trigger_execution_notification


logger = logging.getLogger("app.scheduler")


_task_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def get_task_lock(task_id: str) -> threading.Lock:
    """
    获取任务执行锁
    
    每个任务有独立的锁，防止同一任务并发执行。
    使用全局字典存储锁，确保跨线程共享。
    """
    with _locks_lock:
        if task_id not in _task_locks:
            _task_locks[task_id] = threading.Lock()
        return _task_locks[task_id]


def cleanup_task_lock(task_id: str):
    """清理任务锁（任务删除时调用）"""
    with _locks_lock:
        _task_locks.pop(task_id, None)


class SchedulerService:
    """定时任务调度器服务"""
    
    _instance = None
    _scheduler: AsyncIOScheduler | None = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._scheduler is None:
            self._init_scheduler()
    
    def _init_scheduler(self):
        """初始化调度器"""
        db_url = str(settings.SQLALCHEMY_DATABASE_URI)
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=db_url,
                tablename='apscheduler_jobs'
            )
        }
        
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300
        }
        
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )
    
    def start(self):
        """启动调度器"""
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("scheduler_started")
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("scheduler_shutdown")
    
    def add_job(self, task: ScheduledTask) -> str:
        """添加任务到调度器"""
        job_id = str(task.id)
        trigger = self._create_trigger(task)
        
        if trigger is None:
            raise ValueError(f"无法创建触发器: {task.trigger_type}")
        
        self._scheduler.add_job(
            func=run_scheduled_task,
            trigger=trigger,
            id=job_id,
            args=[str(task.id)],
            name=task.name,
            replace_existing=True,
        )
        
        job = self._scheduler.get_job(job_id)
        next_run = job.next_run_time if job else None
        
        logger.info(
            "task_scheduled",
            extra={
                "task_id": str(task.id),
                "task_name": task.name,
                "trigger_type": task.trigger_type,
                "next_run": str(next_run),
            }
        )
        
        return next_run
    
    def remove_job(self, task_id: uuid.UUID):
        """从调度器移除任务"""
        job_id = str(task_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            cleanup_task_lock(job_id)
            logger.info("task_removed_from_scheduler", extra={"task_id": job_id})
    
    def pause_job(self, task_id: uuid.UUID):
        """暂停任务"""
        job_id = str(task_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.pause_job(job_id)
    
    def resume_job(self, task_id: uuid.UUID):
        """恢复任务"""
        job_id = str(task_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.resume_job(job_id)
    
    def trigger_job(self, task_id: uuid.UUID):
        """立即触发任务"""
        job_id = str(task_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.modify_job(job_id, next_run_time=datetime.now())
            logger.info("task_triggered", extra={"task_id": job_id})
    
    def get_next_run_time(self, task_id: uuid.UUID) -> datetime | None:
        """获取下次执行时间"""
        job_id = str(task_id)
        job = self._scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None
    
    def _create_trigger(self, task: ScheduledTask):
        """创建触发器"""
        try:
            config = json.loads(task.trigger_config)
        except json.JSONDecodeError:
            return None
        
        if task.trigger_type == TriggerType.CRON:
            return self._create_cron_trigger(config)
        elif task.trigger_type == TriggerType.INTERVAL:
            return self._create_interval_trigger(config)
        elif task.trigger_type == TriggerType.DATE:
            return self._create_date_trigger(config)
        
        return None
    
    def _create_cron_trigger(self, config: dict):
        """创建 Cron 触发器"""
        cron_expr = config.get("cron", "")
        if not cron_expr:
            return None
        
        parts = cron_expr.split()
        if len(parts) != 5:
            return None
        
        return CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone='Asia/Shanghai'
        )
    
    def _create_interval_trigger(self, config: dict):
        """创建间隔触发器"""
        minutes = config.get("minutes", 0)
        hours = config.get("hours", 0)
        seconds = config.get("seconds", 0)
        
        if minutes == 0 and hours == 0 and seconds == 0:
            return None
        
        return IntervalTrigger(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            timezone='Asia/Shanghai'
        )
    
    def _create_date_trigger(self, config: dict):
        """创建单次触发器"""
        run_date = config.get("run_date")
        if not run_date:
            return None
        
        if isinstance(run_date, str):
            run_date = datetime.fromisoformat(run_date)
        
        return DateTrigger(run_date=run_date, timezone='Asia/Shanghai')


scheduler_service = SchedulerService()


def run_scheduled_task(task_id: str):
    """
    同步包装器，供 APScheduler 调用
    
    APScheduler 的 ThreadPoolExecutor 无法直接执行 async 函数，
    所以需要这个同步包装器来运行 async 函数。
    
    包含执行锁检查，防止同一任务并发执行。
    """
    task_lock = get_task_lock(task_id)
    
    if not task_lock.acquire(blocking=False):
        logger.warning(
            "task_skipped_concurrent",
            extra={
                "task_id": task_id,
                "reason": "任务正在执行中，跳过本次触发",
            }
        )
        return
    
    try:
        asyncio.run(execute_scheduled_task_with_retry(task_id))
    finally:
        task_lock.release()


async def execute_scheduled_task_with_retry(task_id: str):
    """
    执行定时任务（带重试机制）
    
    执行流程：
    1. 获取任务配置
    2. 检查任务是否启用
    3. 执行任务（带超时控制）
    4. 失败时按配置重试（指数退避）
    5. 更新执行日志和任务状态
    """
    task_uuid = uuid.UUID(task_id)
    
    with Session(engine) as session:
        task = get_task(session=session, task_id=task_uuid)
        
        if not task:
            logger.warning("task_not_found", extra={"task_id": task_id})
            return
        
        if not task.is_enabled:
            logger.info("task_disabled_skipped", extra={"task_id": task_id})
            return
        
        max_retries = task.max_retries or DEFAULT_MAX_RETRIES
        retry_interval = task.retry_interval or DEFAULT_RETRY_INTERVAL
        timeout_seconds = task.timeout_seconds or DEFAULT_TIMEOUT
        
        task_log = create_task_log(
            session=session,
            task_id=task_uuid,
            status="running",
        )
        
        execution = None
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "task_execution_attempt",
                    extra={
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "max_attempts": max_retries + 1,
                    }
                )
                
                update_task_log(
                    session=session,
                    db_log=task_log,
                    attempt_number=attempt + 1,
                    retry_count=attempt,
                )
                
                execution = await asyncio.wait_for(
                    _execute_task_internal(session, task, task_log),
                    timeout=timeout_seconds,
                )
                
                update_task_log(
                    session=session,
                    db_log=task_log,
                    status="completed",
                    finished_at=get_datetime_china(),
                )
                
                logger.info(
                    "task_execution_completed",
                    extra={
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "execution_id": str(execution.id) if execution else None,
                    }
                )
                
                if task.notification_rule_id and execution:
                    project_name = _get_project_name(session, task.project_id)
                    await trigger_execution_notification(
                        session=session,
                        execution=execution,
                        project_name=project_name,
                    )
                
                next_run = scheduler_service.get_next_run_time(task_uuid)
                update_task_run_times(
                    session=session,
                    db_task=task,
                    last_run_at=get_datetime_china(),
                    next_run_at=next_run,
                )
                
                return
                
            except asyncio.TimeoutError:
                last_error = f"任务执行超时（{timeout_seconds}秒）"
                logger.warning(
                    "task_execution_timeout",
                    extra={
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "timeout_seconds": timeout_seconds,
                    }
                )
                
            except Exception as e:
                last_error = str(e)
                logger.error(
                    "task_execution_failed",
                    extra={
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "error": last_error,
                    }
                )
            
            if attempt < max_retries:
                backoff = retry_interval * (RETRY_BACKOFF_FACTOR ** attempt)
                logger.info(
                    "task_retry_scheduled",
                    extra={
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "next_retry_in_seconds": backoff,
                    }
                )
                await asyncio.sleep(backoff)
        
        update_task_log(
            session=session,
            db_log=task_log,
            status="timeout" if "超时" in str(last_error) else "failed",
            error_message=last_error,
            finished_at=get_datetime_china(),
        )
        
        update_task_run_times(
            session=session,
            db_task=task,
            last_run_at=get_datetime_china(),
        )
        
        logger.error(
            "task_execution_final_failure",
            extra={
                "task_id": task_id,
                "total_attempts": max_retries + 1,
                "final_error": last_error,
            }
        )


async def _execute_task_internal(
    session: Session,
    task: ScheduledTask,
    task_log: TaskExecutionLog,
) -> TestExecution | None:
    """
    执行任务的内部实现
    
    创建执行记录并调用 Apifox CLI 执行测试
    """
    project_name = _get_project_name(session, task.project_id)
    
    execution_in = TestExecutionCreate(
        project_id=task.project_id,
        apifox_collection_id=task.collection_id,
        collection_type=task.collection_type,
        environment=task.environment,
        project_name=project_name,
    )
    
    execution = create_execution(session=session, execution_in=execution_in)
    
    update_task_log(
        session=session,
        db_log=task_log,
        execution_id=execution.id,
    )
    
    collection_id = task.collection_id
    collection_type = task.collection_type
    
    if collection_type == "test-scenario" and collection_id.startswith("ts-"):
        collection_id = collection_id[3:]
    elif collection_type == "test-scenario-folder" and collection_id.startswith("tf-"):
        collection_id = collection_id[3:]
    elif collection_type == "test-suite" and collection_id.startswith("suite-"):
        collection_id = collection_id[6:]
    
    execution = await apifox_service.execute_and_save(
        session=session,
        execution=execution,
        collection_id=collection_id,
        environment_id=task.environment,
        collection_type=collection_type,
    )
    
    return execution


def _get_project_name(session: Session, project_id: uuid.UUID | None) -> str | None:
    """获取项目名称"""
    if not project_id:
        return None
    project = get_project(session=session, project_id=project_id)
    return project.name if project else None


def restore_scheduled_tasks():
    """
    恢复所有已启用的定时任务
    
    应用启动时调用，从数据库加载任务到调度器
    """
    with Session(engine) as session:
        from app.crud.scheduled_task import get_enabled_tasks
        
        tasks = get_enabled_tasks(session=session)
        restored_count = 0
        failed_count = 0
        
        for task in tasks:
            try:
                next_run = scheduler_service.add_job(task)
                
                update_task_run_times(
                    session=session,
                    db_task=task,
                    next_run_at=next_run,
                )
                restored_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(
                    "task_restore_failed",
                    extra={
                        "task_id": str(task.id),
                        "task_name": task.name,
                        "error": str(e),
                    }
                )
        
        logger.info(
            "tasks_restored",
            extra={
                "restored": restored_count,
                "failed": failed_count,
            }
        )
