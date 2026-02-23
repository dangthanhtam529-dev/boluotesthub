"""
通知触发器服务

在特定事件发生时触发通知发送
"""

import json
import uuid
from sqlmodel import Session

from app.models.notification import TriggerType
from app.models.execution import TestExecution
from app.crud.notification import (
    get_enabled_rules_by_trigger,
    get_enabled_channels_by_ids,
    create_log,
    mark_log_sent,
    mark_log_failed,
)
from app.services.notification_service import NotificationService, NotificationBuilder


async def trigger_execution_notification(
    session: Session,
    execution: TestExecution,
    project_name: str | None = None,
) -> None:
    """
    触发执行完成通知
    
    根据配置的通知规则，发送执行完成通知
    
    Args:
        session: 数据库会话
        execution: 执行记录
        project_name: 项目名称
    """
    notification_service = NotificationService()
    
    try:
        rules = get_enabled_rules_by_trigger(
            session=session,
            trigger_type=TriggerType.EXECUTION_DONE,
            project_id=execution.project_id,
        )
        
        if execution.status == "failed":
            failed_rules = get_enabled_rules_by_trigger(
                session=session,
                trigger_type=TriggerType.EXECUTION_FAILED,
                project_id=execution.project_id,
            )
            rules = rules + failed_rules
        
        if not rules:
            return
        
        title, content = NotificationBuilder.build_execution_notification(
            execution=execution,
            project_name=project_name,
        )
        
        for rule in rules:
            try:
                channel_ids = json.loads(rule.channel_ids)
                if not channel_ids:
                    continue
                
                channels = get_enabled_channels_by_ids(
                    session=session,
                    channel_ids=[uuid.UUID(cid) for cid in channel_ids],
                )
                
                for channel in channels:
                    log = create_log(
                        session=session,
                        rule_id=rule.id,
                        channel_id=channel.id,
                        channel_type=channel.channel_type,
                        channel_name=channel.name,
                        title=title,
                        content=content,
                        execution_id=execution.id,
                    )
                    
                    success, error = await notification_service.send_to_channel(
                        channel=channel,
                        title=title,
                        content=content,
                    )
                    
                    if success:
                        mark_log_sent(session=session, db_log=log)
                    else:
                        mark_log_failed(session=session, db_log=log, error_message=error)
                        
            except Exception as e:
                print(f"发送通知失败 (规则: {rule.name}): {e}")
                continue
                
    finally:
        await notification_service.close()


async def trigger_threshold_alert(
    session: Session,
    execution: TestExecution,
    project_name: str | None = None,
    threshold: float = 80.0,
) -> None:
    """
    触发阈值告警
    
    当通过率低于阈值时发送告警
    
    Args:
        session: 数据库会话
        execution: 执行记录
        project_name: 项目名称
        threshold: 通过率阈值（默认 80%）
    """
    if not execution.total_cases or execution.total_cases == 0:
        return
    
    pass_rate = (execution.passed_cases or 0) / execution.total_cases * 100
    if pass_rate >= threshold:
        return
    
    notification_service = NotificationService()
    
    try:
        rules = get_enabled_rules_by_trigger(
            session=session,
            trigger_type=TriggerType.THRESHOLD_ALERT,
            project_id=execution.project_id,
        )
        
        if not rules:
            return
        
        title, content = NotificationBuilder.build_threshold_alert(
            execution=execution,
            project_name=project_name,
            threshold=threshold,
        )
        
        for rule in rules:
            try:
                channel_ids = json.loads(rule.channel_ids)
                if not channel_ids:
                    continue
                
                channels = get_enabled_channels_by_ids(
                    session=session,
                    channel_ids=[uuid.UUID(cid) for cid in channel_ids],
                )
                
                for channel in channels:
                    log = create_log(
                        session=session,
                        rule_id=rule.id,
                        channel_id=channel.id,
                        channel_type=channel.channel_type,
                        channel_name=channel.name,
                        title=title,
                        content=content,
                        execution_id=execution.id,
                    )
                    
                    success, error = await notification_service.send_to_channel(
                        channel=channel,
                        title=title,
                        content=content,
                    )
                    
                    if success:
                        mark_log_sent(session=session, db_log=log)
                    else:
                        mark_log_failed(session=session, db_log=log, error_message=error)
                        
            except Exception as e:
                print(f"发送告警失败 (规则: {rule.name}): {e}")
                continue
                
    finally:
        await notification_service.close()
