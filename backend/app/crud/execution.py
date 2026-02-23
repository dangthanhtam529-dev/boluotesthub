# 测试执行相关 CRUD 操作
import uuid
from datetime import datetime
from sqlmodel import Session, select, desc, func
from app.models.execution import (
    TestExecution,
    TestExecutionCreate,
    TestExecutionUpdate,
    ExecutionStatus,
    ExecutionStats,
)
from app.models.base import get_datetime_china


def create_execution(*, session: Session, execution_in: TestExecutionCreate) -> TestExecution:
    """创建新的测试执行记录"""
    db_execution = TestExecution.model_validate(execution_in)
    session.add(db_execution)
    session.commit()
    session.refresh(db_execution)
    return db_execution


def get_execution(*, session: Session, execution_id: uuid.UUID) -> TestExecution | None:
    """通过 ID 获取测试执行记录"""
    statement = select(TestExecution).where(TestExecution.id == execution_id)
    return session.exec(statement).first()


def get_executions(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    collection_id: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[TestExecution]:
    """获取测试执行记录列表（支持筛选）"""
    statement = select(TestExecution)
    
    if status:
        statement = statement.where(TestExecution.status == status)
    if collection_id:
        statement = statement.where(TestExecution.apifox_collection_id == collection_id)
    if project_id:
        statement = statement.where(TestExecution.project_id == uuid.UUID(project_id))
    if project_name:
        statement = statement.where(TestExecution.project_name.contains(project_name))
    if start_date:
        statement = statement.where(TestExecution.created_at >= start_date)
    if end_date:
        statement = statement.where(TestExecution.created_at <= end_date)
    
    statement = statement.order_by(desc(TestExecution.created_at)).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_executions(
    *,
    session: Session,
    status: str | None = None,
    collection_id: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """获取执行记录总数（支持筛选）"""
    statement = select(func.count()).select_from(TestExecution)
    
    if status:
        statement = statement.where(TestExecution.status == status)
    if collection_id:
        statement = statement.where(TestExecution.apifox_collection_id == collection_id)
    if project_id:
        statement = statement.where(TestExecution.project_id == uuid.UUID(project_id))
    if project_name:
        statement = statement.where(TestExecution.project_name.contains(project_name))
    if start_date:
        statement = statement.where(TestExecution.created_at >= start_date)
    if end_date:
        statement = statement.where(TestExecution.created_at <= end_date)
    
    return session.exec(statement).one()


def update_execution(
    *,
    session: Session,
    db_execution: TestExecution,
    execution_in: TestExecutionUpdate | dict,
) -> TestExecution:
    """更新测试执行记录"""
    if isinstance(execution_in, dict):
        update_data = execution_in
    else:
        update_data = execution_in.model_dump(exclude_unset=True)
    
    db_execution.sqlmodel_update(update_data)
    session.add(db_execution)
    session.commit()
    session.refresh(db_execution)
    return db_execution


def delete_execution(*, session: Session, db_execution: TestExecution) -> None:
    """删除测试执行记录"""
    session.delete(db_execution)
    session.commit()


def get_execution_stats(*, session: Session) -> ExecutionStats:
    """获取执行统计数据"""
    # 总执行次数
    total_count = session.exec(select(func.count()).select_from(TestExecution)).one()
    
    # 成功次数
    passed_count = session.exec(
        select(func.count())
        .select_from(TestExecution)
        .where(TestExecution.status == ExecutionStatus.COMPLETED)
    ).one()
    
    # 失败次数
    failed_count = session.exec(
        select(func.count())
        .select_from(TestExecution)
        .where(TestExecution.status == ExecutionStatus.FAILED)
    ).one()
    
    # 计算通过率
    pass_rate = 0.0
    if total_count > 0:
        pass_rate = round(passed_count / total_count * 100, 2)
    
    # 获取最近执行记录
    recent_statement = (
        select(TestExecution)
        .order_by(desc(TestExecution.created_at))
        .limit(5)
    )
    recent_executions = list(session.exec(recent_statement).all())
    
    return ExecutionStats(
        total_executions=total_count,
        total_passed=passed_count,
        total_failed=failed_count,
        pass_rate=pass_rate,
        recent_executions=recent_executions,
    )


def mark_execution_started(*, session: Session, execution_id: uuid.UUID) -> TestExecution | None:
    """标记执行开始"""
    db_execution = get_execution(session=session, execution_id=execution_id)
    if not db_execution:
        return None
    
    db_execution.status = ExecutionStatus.RUNNING
    db_execution.started_at = get_datetime_china()
    session.add(db_execution)
    session.commit()
    session.refresh(db_execution)
    return db_execution


def mark_execution_completed(
    *,
    session: Session,
    execution_id: uuid.UUID,
    total_cases: int,
    passed_cases: int,
    failed_cases: int,
    report_json: str | None = None,
) -> TestExecution | None:
    """标记执行完成"""
    db_execution = get_execution(session=session, execution_id=execution_id)
    if not db_execution:
        return None
    
    db_execution.status = ExecutionStatus.COMPLETED
    db_execution.completed_at = get_datetime_china()
    db_execution.total_cases = total_cases
    db_execution.passed_cases = passed_cases
    db_execution.failed_cases = failed_cases
    if report_json:
        db_execution.report_json = report_json
    
    session.add(db_execution)
    session.commit()
    session.refresh(db_execution)
    return db_execution


def mark_execution_failed(
    *,
    session: Session,
    execution_id: uuid.UUID,
    error_message: str,
) -> TestExecution | None:
    """标记执行失败"""
    db_execution = get_execution(session=session, execution_id=execution_id)
    if not db_execution:
        return None
    
    db_execution.status = ExecutionStatus.FAILED
    db_execution.completed_at = get_datetime_china()
    db_execution.error_message = error_message
    
    session.add(db_execution)
    session.commit()
    session.refresh(db_execution)
    return db_execution