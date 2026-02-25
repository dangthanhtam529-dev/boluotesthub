"""
通知触发器服务

在特定事件发生时触发通知发送

关键修复：定时任务环境下需要重新加载环境变量，确保能获取到正确的配置
"""

import json
import uuid
import os
import logging
from sqlmodel import Session

logger = logging.getLogger("app.notification_trigger")

# 关键修复：定时任务环境下需要重新加载环境变量
# 确保能获取到正确的配置
def reload_env_for_scheduled_task():
    """
    重新加载环境变量（定时任务环境下使用）
    
    定时任务默认工作目录是 C:\Windows\System32，需要切换到项目目录并重新加载 .env 文件
    """
    # 获取项目根目录
    current_file = os.path.abspath(__file__)
    # 向上遍历到 backend/app/services，再向上两级到项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    
    logger.info(f"通知服务 - 当前工作目录：{os.getcwd()}")
    logger.info(f"通知服务 - 项目根目录：{project_root}")
    
    # 切换工作目录
    os.chdir(project_root)
    logger.info(f"通知服务 - 切换后工作目录：{os.getcwd()}")
    
    # 重新加载 .env 文件
    from dotenv import load_dotenv
    env_file_path = os.path.join(project_root, ".env")
    logger.info(f"通知服务 - 重新加载 .env 文件：{env_file_path}")
    load_dotenv(env_file_path, override=True)
    
    logger.info(f"通知服务 - 重新加载后 APIFOX_ACCESS_TOKEN 是否存在：{'APIFOX_ACCESS_TOKEN' in os.environ}")
    logger.info(f"通知服务 - 重新加载后 APIFOX_PROJECT_ID: {os.environ.get('APIFOX_PROJECT_ID', 'NOT SET')}")

from app.models.notification import TriggerType
from app.models.execution import TestExecution
from app.crud.notification import (
    get_enabled_rules_by_trigger,
    get_enabled_channels_by_ids,
    get_rule,
    create_log,
    mark_log_sent,
    mark_log_failed,
)
from app.services.notification_service import NotificationService, NotificationBuilder


def trigger_execution_notification(
    session: Session,
    execution: TestExecution,
    project_name: str | None = None,
    notification_rule_id: uuid.UUID | None = None,
) -> None:
    """
    触发执行完成通知（纯同步版本）
    
    Args:
        session: 数据库会话
        execution: 执行记录
        project_name: 项目名称
        notification_rule_id: 指定的通知规则 ID（优先级高于自动查询）
    """
    # 关键修复：定时任务环境下需要重新加载环境变量
    reload_env_for_scheduled_task()
    
    notification_service = NotificationService()
    
    print(f"触发执行通知：execution_id={execution.id}, project_id={execution.project_id}, notification_rule_id={notification_rule_id}")
    
    try:
        rules = []
        
        # 如果指定了通知规则 ID，优先使用
        if notification_rule_id:
            logger.info(f"使用指定的通知规则：{notification_rule_id}")
            rule = get_rule(session=session, rule_id=notification_rule_id)
            if rule:
                print(f"找到规则：{rule.name}, is_enabled={rule.is_enabled}")
                if rule.is_enabled:
                    rules = [rule]
            else:
                print(f"未找到规则：{notification_rule_id}")
        
        # 如果没有指定规则或规则不可用，则自动查询
        if not rules:
            print(f"自动查询规则：trigger_type={TriggerType.EXECUTION_DONE}, project_id={execution.project_id}")
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
        
        logger.info(f"找到 {len(rules)} 条通知规则")
        
        if not rules:
            logger.info("没有可用的通知规则，跳过通知")
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
                    
                    print(f"开始发送通知到渠道：{channel.name} ({channel.channel_type})")
                    success, error = notification_service.send_to_channel(
                        channel=channel,
                        title=title,
                        content=content,
                    )
                    
                    if success:
                        print(f"通知发送成功：{channel.name}")
                        mark_log_sent(session=session, db_log=log)
                    else:
                        print(f"通知发送失败：{channel.name}, 错误：{error}")
                        mark_log_failed(session=session, db_log=log, error_message=error)
                        
            except Exception as e:
                print(f"发送通知失败 (规则：{rule.name}): {e}")
                continue
                
    finally:
        notification_service.close()


def trigger_threshold_alert(
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
                    
                    success, error = notification_service.send_to_channel(
                        channel=channel,
                        title=title,
                        content=content,
                    )
                    
                    if success:
                        mark_log_sent(session=session, db_log=log)
                    else:
                        mark_log_failed(session=session, db_log=log, error_message=error)
                        
            except Exception as e:
                print(f"发送告警失败 (规则：{rule.name}): {e}")
                continue
                
    finally:
        notification_service.close()