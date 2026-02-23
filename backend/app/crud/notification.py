"""
通知模块 CRUD 操作
"""

import uuid
from datetime import datetime
from sqlmodel import Session, select, desc, func
from app.models.notification import (
    NotificationChannel,
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationRule,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationLog,
    NotificationStatus,
)
from app.models.base import get_datetime_china


# ============================================================================
# 通知渠道 CRUD
# ============================================================================

def create_channel(*, session: Session, channel_in: NotificationChannelCreate) -> NotificationChannel:
    """创建通知渠道"""
    db_channel = NotificationChannel.model_validate(channel_in)
    session.add(db_channel)
    session.commit()
    session.refresh(db_channel)
    return db_channel


def get_channel(*, session: Session, channel_id: uuid.UUID) -> NotificationChannel | None:
    """获取单个通知渠道"""
    statement = select(NotificationChannel).where(NotificationChannel.id == channel_id)
    return session.exec(statement).first()


def get_channels(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    channel_type: str | None = None,
    is_enabled: bool | None = None,
) -> list[NotificationChannel]:
    """获取通知渠道列表"""
    statement = select(NotificationChannel)
    
    if channel_type:
        statement = statement.where(NotificationChannel.channel_type == channel_type)
    if is_enabled is not None:
        statement = statement.where(NotificationChannel.is_enabled == is_enabled)
    
    statement = statement.order_by(desc(NotificationChannel.created_at)).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_channels(
    *,
    session: Session,
    channel_type: str | None = None,
    is_enabled: bool | None = None,
) -> int:
    """统计通知渠道数量"""
    statement = select(func.count()).select_from(NotificationChannel)
    
    if channel_type:
        statement = statement.where(NotificationChannel.channel_type == channel_type)
    if is_enabled is not None:
        statement = statement.where(NotificationChannel.is_enabled == is_enabled)
    
    return session.exec(statement).one()


def update_channel(
    *,
    session: Session,
    db_channel: NotificationChannel,
    channel_in: NotificationChannelUpdate | dict,
) -> NotificationChannel:
    """更新通知渠道"""
    if isinstance(channel_in, dict):
        update_data = channel_in
    else:
        update_data = channel_in.model_dump(exclude_unset=True)
    
    db_channel.sqlmodel_update(update_data)
    db_channel.updated_at = get_datetime_china()
    session.add(db_channel)
    session.commit()
    session.refresh(db_channel)
    return db_channel


def delete_channel(*, session: Session, db_channel: NotificationChannel) -> None:
    """删除通知渠道"""
    session.delete(db_channel)
    session.commit()


def get_enabled_channels_by_ids(*, session: Session, channel_ids: list[uuid.UUID]) -> list[NotificationChannel]:
    """根据 ID 列表获取已启用的渠道"""
    statement = select(NotificationChannel).where(
        NotificationChannel.id.in_(channel_ids),
        NotificationChannel.is_enabled == True,
    )
    return list(session.exec(statement).all())


# ============================================================================
# 通知规则 CRUD
# ============================================================================

def create_rule(*, session: Session, rule_in: NotificationRuleCreate) -> NotificationRule:
    """创建通知规则"""
    db_rule = NotificationRule.model_validate(rule_in)
    session.add(db_rule)
    session.commit()
    session.refresh(db_rule)
    return db_rule


def get_rule(*, session: Session, rule_id: uuid.UUID) -> NotificationRule | None:
    """获取单个通知规则"""
    statement = select(NotificationRule).where(NotificationRule.id == rule_id)
    return session.exec(statement).first()


def get_rules(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    trigger_type: str | None = None,
    project_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
) -> list[NotificationRule]:
    """获取通知规则列表"""
    statement = select(NotificationRule)
    
    if trigger_type:
        statement = statement.where(NotificationRule.trigger_type == trigger_type)
    if project_id:
        statement = statement.where(NotificationRule.project_id == project_id)
    if is_enabled is not None:
        statement = statement.where(NotificationRule.is_enabled == is_enabled)
    
    statement = statement.order_by(desc(NotificationRule.created_at)).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_rules(
    *,
    session: Session,
    trigger_type: str | None = None,
    project_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
) -> int:
    """统计通知规则数量"""
    statement = select(func.count()).select_from(NotificationRule)
    
    if trigger_type:
        statement = statement.where(NotificationRule.trigger_type == trigger_type)
    if project_id:
        statement = statement.where(NotificationRule.project_id == project_id)
    if is_enabled is not None:
        statement = statement.where(NotificationRule.is_enabled == is_enabled)
    
    return session.exec(statement).one()


def update_rule(
    *,
    session: Session,
    db_rule: NotificationRule,
    rule_in: NotificationRuleUpdate | dict,
) -> NotificationRule:
    """更新通知规则"""
    if isinstance(rule_in, dict):
        update_data = rule_in
    else:
        update_data = rule_in.model_dump(exclude_unset=True)
    
    db_rule.sqlmodel_update(update_data)
    db_rule.updated_at = get_datetime_china()
    session.add(db_rule)
    session.commit()
    session.refresh(db_rule)
    return db_rule


def delete_rule(*, session: Session, db_rule: NotificationRule) -> None:
    """删除通知规则"""
    session.delete(db_rule)
    session.commit()


def get_enabled_rules_by_trigger(
    *,
    session: Session,
    trigger_type: str,
    project_id: uuid.UUID | None = None,
) -> list[NotificationRule]:
    """获取指定触发类型的已启用规则"""
    statement = select(NotificationRule).where(
        NotificationRule.trigger_type == trigger_type,
        NotificationRule.is_enabled == True,
    )
    
    if project_id:
        statement = statement.where(
            (NotificationRule.project_id == project_id) | (NotificationRule.project_id.is_(None))
        )
    
    return list(session.exec(statement).all())


# ============================================================================
# 通知日志 CRUD
# ============================================================================

def create_log(
    *,
    session: Session,
    rule_id: uuid.UUID | None = None,
    channel_id: uuid.UUID | None = None,
    channel_type: str,
    channel_name: str,
    title: str,
    content: str,
    execution_id: uuid.UUID | None = None,
) -> NotificationLog:
    """创建通知日志"""
    db_log = NotificationLog(
        rule_id=rule_id,
        channel_id=channel_id,
        channel_type=channel_type,
        channel_name=channel_name,
        title=title,
        content=content,
        status=NotificationStatus.PENDING,
        execution_id=execution_id,
    )
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


def get_log(*, session: Session, log_id: uuid.UUID) -> NotificationLog | None:
    """获取单个通知日志"""
    statement = select(NotificationLog).where(NotificationLog.id == log_id)
    return session.exec(statement).first()


def get_logs(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    channel_type: str | None = None,
    status: str | None = None,
    execution_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[NotificationLog]:
    """获取通知日志列表"""
    statement = select(NotificationLog)
    
    if channel_type:
        statement = statement.where(NotificationLog.channel_type == channel_type)
    if status:
        statement = statement.where(NotificationLog.status == status)
    if execution_id:
        statement = statement.where(NotificationLog.execution_id == execution_id)
    if start_date:
        statement = statement.where(NotificationLog.created_at >= start_date)
    if end_date:
        statement = statement.where(NotificationLog.created_at <= end_date)
    
    statement = statement.order_by(desc(NotificationLog.created_at)).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_logs(
    *,
    session: Session,
    channel_type: str | None = None,
    status: str | None = None,
    execution_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """统计通知日志数量"""
    statement = select(func.count()).select_from(NotificationLog)
    
    if channel_type:
        statement = statement.where(NotificationLog.channel_type == channel_type)
    if status:
        statement = statement.where(NotificationLog.status == status)
    if execution_id:
        statement = statement.where(NotificationLog.execution_id == execution_id)
    if start_date:
        statement = statement.where(NotificationLog.created_at >= start_date)
    if end_date:
        statement = statement.where(NotificationLog.created_at <= end_date)
    
    return session.exec(statement).one()


def mark_log_sent(*, session: Session, db_log: NotificationLog) -> NotificationLog:
    """标记通知发送成功"""
    db_log.status = NotificationStatus.SENT
    db_log.sent_at = get_datetime_china()
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


def mark_log_failed(*, session: Session, db_log: NotificationLog, error_message: str) -> NotificationLog:
    """标记通知发送失败"""
    db_log.status = NotificationStatus.FAILED
    db_log.error_message = error_message
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log
