"""
通知模块 API 路由
"""

import uuid
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models import Message
from app.models.notification import (
    NotificationChannel,
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelPublic,
    NotificationChannelsPublic,
    NotificationRule,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRulePublic,
    NotificationRulesPublic,
    NotificationLogPublic,
    NotificationLogsPublic,
    TestNotificationRequest,
    TestNotificationResponse,
)
from app.crud.notification import (
    create_channel,
    get_channel,
    get_channels,
    count_channels,
    update_channel,
    delete_channel,
    create_rule,
    get_rule,
    get_rules,
    count_rules,
    update_rule,
    delete_rule,
    get_logs,
    count_logs,
    create_log,
    mark_log_sent,
    mark_log_failed,
)
from app.services.notification_service import NotificationService, NotificationBuilder


router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============================================================================
# 通知渠道 API
# ============================================================================

@router.get("/channels", response_model=NotificationChannelsPublic)
def read_channels(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    channel_type: str | None = None,
    is_enabled: bool | None = None,
) -> Any:
    """获取通知渠道列表"""
    channels = get_channels(
        session=session,
        skip=skip,
        limit=limit,
        channel_type=channel_type,
        is_enabled=is_enabled,
    )
    count = count_channels(
        session=session,
        channel_type=channel_type,
        is_enabled=is_enabled,
    )
    return NotificationChannelsPublic(data=channels, count=count)


@router.get("/channels/{channel_id}", response_model=NotificationChannelPublic)
def read_channel(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    channel_id: uuid.UUID,
) -> Any:
    """获取单个通知渠道"""
    channel = get_channel(session=session, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    return channel


@router.post("/channels", response_model=NotificationChannelPublic)
def create_channel_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    channel_in: NotificationChannelCreate,
) -> Any:
    """创建通知渠道"""
    channel = create_channel(session=session, channel_in=channel_in)
    return channel


@router.put("/channels/{channel_id}", response_model=NotificationChannelPublic)
def update_channel_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    channel_id: uuid.UUID,
    channel_in: NotificationChannelUpdate,
) -> Any:
    """更新通知渠道"""
    channel = get_channel(session=session, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    channel = update_channel(session=session, db_channel=channel, channel_in=channel_in)
    return channel


@router.delete("/channels/{channel_id}", response_model=Message)
def delete_channel_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    channel_id: uuid.UUID,
) -> Any:
    """删除通知渠道"""
    channel = get_channel(session=session, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    delete_channel(session=session, db_channel=channel)
    return Message(message="删除成功")


@router.post("/channels/test", response_model=TestNotificationResponse)
async def test_channel(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    request: TestNotificationRequest,
) -> Any:
    """测试通知渠道"""
    channel = get_channel(session=session, channel_id=request.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    
    title, content = NotificationBuilder.build_test_message(channel.name)
    
    if request.test_message:
        content = f"### 🔔 通知测试\n\n**渠道**: {channel.name}\n\n{request.test_message}\n\n⏰ 发送时间: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S') if channel.created_at else '未知'}"
    
    notification_service = NotificationService()
    try:
        success, error = await notification_service.send_to_channel(
            channel=channel,
            title=title,
            content=content,
        )
        
        if success:
            return TestNotificationResponse(success=True, message="发送成功")
        else:
            return TestNotificationResponse(success=False, message="发送失败", error=error)
    finally:
        await notification_service.close()


# ============================================================================
# 通知规则 API
# ============================================================================

@router.get("/rules", response_model=NotificationRulesPublic)
def read_rules(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    trigger_type: str | None = None,
    project_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
) -> Any:
    """获取通知规则列表"""
    rules = get_rules(
        session=session,
        skip=skip,
        limit=limit,
        trigger_type=trigger_type,
        project_id=project_id,
        is_enabled=is_enabled,
    )
    count = count_rules(
        session=session,
        trigger_type=trigger_type,
        project_id=project_id,
        is_enabled=is_enabled,
    )
    return NotificationRulesPublic(data=rules, count=count)


@router.get("/rules/{rule_id}", response_model=NotificationRulePublic)
def read_rule(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    rule_id: uuid.UUID,
) -> Any:
    """获取单个通知规则"""
    rule = get_rule(session=session, rule_id=rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="通知规则不存在")
    return rule


@router.post("/rules", response_model=NotificationRulePublic)
def create_rule_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    rule_in: NotificationRuleCreate,
) -> Any:
    """创建通知规则"""
    rule = create_rule(session=session, rule_in=rule_in)
    return rule


@router.put("/rules/{rule_id}", response_model=NotificationRulePublic)
def update_rule_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    rule_id: uuid.UUID,
    rule_in: NotificationRuleUpdate,
) -> Any:
    """更新通知规则"""
    rule = get_rule(session=session, rule_id=rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="通知规则不存在")
    rule = update_rule(session=session, db_rule=rule, rule_in=rule_in)
    return rule


@router.delete("/rules/{rule_id}", response_model=Message)
def delete_rule_endpoint(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    rule_id: uuid.UUID,
) -> Any:
    """删除通知规则"""
    rule = get_rule(session=session, rule_id=rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="通知规则不存在")
    delete_rule(session=session, db_rule=rule)
    return Message(message="删除成功")


# ============================================================================
# 通知日志 API
# ============================================================================

@router.get("/logs", response_model=NotificationLogsPublic)
def read_logs(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    channel_type: str | None = None,
    status: str | None = None,
    execution_id: uuid.UUID | None = None,
) -> Any:
    """获取通知日志列表"""
    logs = get_logs(
        session=session,
        skip=skip,
        limit=limit,
        channel_type=channel_type,
        status=status,
        execution_id=execution_id,
    )
    count = count_logs(
        session=session,
        channel_type=channel_type,
        status=status,
        execution_id=execution_id,
    )
    return NotificationLogsPublic(data=logs, count=count)
