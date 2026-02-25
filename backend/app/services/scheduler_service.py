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
from app.services.apifox import apifox_service, ApifoxCliError
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


def safe_async_run(coro):
    """
    安全地运行异步协程，自动检测是否在事件循环中运行
    
    在定时任务线程池中运行时，主线程可能已经有事件循环，
    直接调用 asyncio.run() 会报 "got Future attached to a different loop" 错误。
    此函数自动检测并选择合适的执行方式。
    """
    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_running_loop()
        # 如果在事件循环中，需要在新线程中运行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # 没有运行的事件循环，直接使用 asyncio.run
        return asyncio.run(coro)


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
    import os
    
    # 关键修复：定时任务环境下需要显式设置工作目录和重新加载环境变量
    # Windows 定时任务默认工作目录是 C:\Windows\System32，需要切换到项目目录
    backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    project_root = os.path.dirname(backend_dir)
    
    logger.info(f"定时任务开始执行 - 任务 ID: {task_id}")
    logger.info(f"定时任务环境信息 - 当前工作目录：{os.getcwd()}")
    logger.info(f"定时任务环境信息 - 切换到项目目录：{project_root}")
    logger.info(f"定时任务环境信息 - 当前用户：{os.environ.get('USERNAME', 'N/A')}")
    logger.info(f"定时任务环境信息 - APIFOX_ACCESS_TOKEN 是否存在：{'APIFOX_ACCESS_TOKEN' in os.environ}")
    
    # 切换工作目录到项目根目录，确保 .env 文件能被正确读取
    os.chdir(project_root)
    logger.info(f"定时任务环境信息 - 切换后工作目录：{os.getcwd()}")
    
    # 关键修复 1：设置字符编码为 UTF-8，防止 CLI 输出乱码
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # 关键修复 2：确保 npx/npm 能找到
    # Windows 定时任务环境下 PATH 可能不完整，需要显式添加 npm 全局路径
    npm_global_path = os.path.join(os.environ.get('APPDATA', ''), 'npm')
    node_path = r"C:\Program Files\nodejs"
    current_path = os.environ.get('PATH', '')
    
    new_paths = [p for p in [node_path, npm_global_path] if os.path.exists(p) and p not in current_path]
    if new_paths:
        os.environ['PATH'] = os.pathsep.join(new_paths + [current_path])
        logger.info(f"定时任务环境信息 - 已添加 PATH: {new_paths}")
    
    logger.info(f"定时任务环境信息 - 更新后 PATH 前缀：{os.environ.get('PATH', '')[:200]}...")
    
    # 重新加载环境变量（定时任务环境下 .env 可能未被加载）
    from dotenv import load_dotenv
    env_file_path = os.path.join(project_root, ".env")
    logger.info(f"定时任务环境信息 - 尝试重新加载 .env 文件：{env_file_path}")
    load_dotenv(env_file_path, override=True)
    logger.info(f"定时任务环境信息 - 重新加载后 APIFOX_ACCESS_TOKEN 是否存在：{'APIFOX_ACCESS_TOKEN' in os.environ}")
    logger.info(f"定时任务环境信息 - 重新加载后 APIFOX_PROJECT_ID: {os.environ.get('APIFOX_PROJECT_ID', 'NOT SET')}")
    
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
        safe_async_run(execute_scheduled_task_with_retry(task_id))
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
    
    关键修复：添加超时自动恢复机制，防止任务永久卡住
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
        start_time = datetime.now()
        
        # 关键修复：检查是否有卡住的旧执行记录（超过 2 倍超时时间仍在运行）
        if task_log.execution_id:
            from app.crud.execution import get_execution
            old_execution = get_execution(session=session, execution_id=task_log.execution_id)
            if old_execution and old_execution.status == "running" and old_execution.started_at:
                elapsed = (datetime.now() - old_execution.started_at.replace(tzinfo=None)).total_seconds()
                if elapsed > timeout_seconds * 2:
                    logger.warning(f"检测到卡住的执行记录 {task_log.execution_id}，已运行 {elapsed:.0f}秒，标记为失败")
                    old_execution.status = "failed"
                    old_execution.error_message = "任务执行超时，自动终止"
                    old_execution.completed_at = get_datetime_china()
                    session.commit()
        
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
                    try:
                        logger.info(f"开始触发钉钉通知 - execution_id: {execution.id}, status: {execution.status}")
                        await trigger_execution_notification(
                            session=session,
                            execution=execution,
                            project_name=project_name,
                            notification_rule_id=task.notification_rule_id,
                        )
                        logger.info("钉钉通知触发完成")
                    except Exception as notify_err:
                        logger.error(f"触发钉钉通知失败：{notify_err}", exc_info=True)
                        # 通知失败不影响任务状态，只记录日志
                
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
                # 关键修复：超时后立即恢复执行记录状态
                if execution and execution.status == "running":
                    try:
                        execution.status = "failed"
                        execution.error_message = last_error
                        execution.completed_at = get_datetime_china()
                        session.commit()
                    except Exception:
                        session.rollback()
                
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
                # 关键修复：异常后立即恢复执行记录状态
                if execution and execution.status == "running":
                    try:
                        execution.status = "failed"
                        execution.error_message = f"执行异常：{last_error}"
                        execution.completed_at = get_datetime_china()
                        session.commit()
                    except Exception:
                        session.rollback()
            
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
    
    关键修复：定时任务环境下需要显式传递 access_token 和 project_id，
    因为 settings 可能在定时任务环境下读取不到 .env 配置。
    """
    import os
    
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
    
    # 关键修复：定时任务环境下，settings 可能读取不到 .env 配置
    # 需要直接从环境变量获取，确保能读取到最新的配置
    apifox_project_id = os.environ.get("APIFOX_PROJECT_ID") or settings.APIFOX_PROJECT_ID
    access_token = os.environ.get("APIFOX_ACCESS_TOKEN")
    
    logger.info(
        "scheduled_task_apifox_config",
        extra={
            "task_id": str(task.id),
            "apifox_project_id": apifox_project_id,
            "access_token_exists": bool(access_token),
            "access_token_prefix": access_token[:10] + "..." if access_token else "N/A",
        }
    )
    
    if not access_token:
        logger.error("scheduled_task_missing_access_token", extra={"task_id": str(task.id)})
        raise ApifoxCliError("缺少 Apifox access_token，请检查 .env 文件或环境变量配置")
    
    if not apifox_project_id:
        logger.error("scheduled_task_missing_project_id", extra={"task_id": str(task.id)})
        raise ApifoxCliError("缺少 Apifox project_id，请检查 .env 文件或环境变量配置")
    
    # 显式传递 access_token 和 project_id，确保 apifox_service 能正确执行
    # 关键修复：将 access_token 和 project_id 同时设置到环境变量中，确保 CLI 能正确读取
    os.environ["APIFOX_ACCESS_TOKEN"] = access_token
    os.environ["APIFOX_PROJECT_ID"] = apifox_project_id
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    
    # 关键修复：确保 npx 能找到
    npm_global_path = os.path.join(os.environ.get('APPDATA', ''), 'npm')
    node_path = r"C:\Program Files\nodejs"
    current_path = os.environ.get('PATH', '')
    new_paths = [p for p in [node_path, npm_global_path] if os.path.exists(p) and p not in current_path]
    if new_paths:
        os.environ['PATH'] = os.pathsep.join(new_paths + [current_path])
    
    logger.info(f"[定时任务执行] task_id: {task.id}")
    logger.info(f"[定时任务执行] collection_id (原始): {task.collection_id}")
    logger.info(f"[定时任务执行] collection_id (处理后): {collection_id}")
    logger.info(f"[定时任务执行] collection_type: {collection_type}")
    logger.info(f"[定时任务执行] environment: {task.environment}")
    logger.info(f"[定时任务执行] apifox_project_id: {apifox_project_id}")
    logger.info(f"[定时任务执行] access_token 前缀：{access_token[:10]}..." if access_token else "[定时任务执行] access_token: 空")
    logger.info(f"[定时任务执行] 当前工作目录：{os.getcwd()}")
    logger.info(f"[定时任务执行] PATH 前缀：{os.environ.get('PATH', '')[:200]}...")
    
    logger.info(
        "scheduled_task_before_execute",
        extra={
            "task_id": str(task.id),
            "collection_id": collection_id,
            "collection_type": collection_type,
            "environment_id": task.environment,
            "access_token_prefix": access_token[:15] + "..." if access_token else "N/A",
            "project_id": apifox_project_id,
        }
    )
    
    execution = await apifox_service.execute_and_save(
        session=session,
        execution=execution,
        collection_id=collection_id,
        environment_id=task.environment,
        collection_type=collection_type,
        access_token=access_token,  # 显式传递 access_token
        project_id=apifox_project_id,  # 显式传递 project_id
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
