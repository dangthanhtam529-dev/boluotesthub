"""
缺陷管理 CRUD 操作

核心功能：
- 创建缺陷（支持去重）
- 批量创建缺陷
- 查询与筛选
- 统计分析
- 趋势分析
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select, func

from app.models.base import get_datetime_china
from app.models.defect import (
    Defect,
    DefectCreate,
    DefectUpdate,
    DefectStats,
    DefectTrend,
    DefectDedupResult,
    DefectSource,
    DefectSeverity,
    ErrorType,
    generate_fingerprint,
)


def _parse_tags(tags: str | None) -> list[str] | None:
    """解析标签JSON"""
    if not tags:
        return None
    try:
        return json.loads(tags)
    except json.JSONDecodeError:
        return None


def _dump_tags(tags: list[str] | None) -> str | None:
    """序列化标签为JSON"""
    if not tags:
        return None
    return json.dumps(tags, ensure_ascii=False)


def create_defect(
    *,
    session: Session,
    project_id: uuid.UUID,
    defect_in: DefectCreate,
    check_duplicate: bool = True,
) -> tuple[Defect, bool]:
    """
    创建缺陷
    
    Args:
        session: 数据库会话
        project_id: 项目ID
        defect_in: 创建数据
        check_duplicate: 是否检查重复
        
    Returns:
        (缺陷对象, 是否为重复)
    """
    fingerprint = defect_in.fingerprint
    if not fingerprint and defect_in.api_path:
        fingerprint = generate_fingerprint(
            api_path=defect_in.api_path,
            api_method=defect_in.api_method,
            error_type=defect_in.error_type,
            error_message=defect_in.error_detail,
        )
    
    if check_duplicate and fingerprint:
        existing = session.exec(
            select(Defect).where(
                Defect.project_id == project_id,
                Defect.fingerprint == fingerprint,
            )
        ).first()
        
        if existing:
            existing.occurrence_count += 1
            existing.updated_at = get_datetime_china()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing, True
    
    db_defect = Defect(
        project_id=project_id,
        title=defect_in.title,
        description=defect_in.description,
        source=defect_in.source,
        source_id=defect_in.source_id,
        api_path=defect_in.api_path,
        api_method=defect_in.api_method,
        module=defect_in.module,
        error_type=defect_in.error_type,
        request_data=defect_in.request_data,
        response_data=defect_in.response_data,
        error_detail=defect_in.error_detail,
        severity=defect_in.severity,
        tags=_dump_tags(defect_in.tags),
        fingerprint=fingerprint,
    )
    session.add(db_defect)
    session.commit()
    session.refresh(db_defect)
    return db_defect, False


def create_defect_from_execution(
    *,
    session: Session,
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    api_path: str,
    api_method: str,
    error_type: str,
    error_detail: str,
    request_data: str | None = None,
    response_data: str | None = None,
    module: str | None = None,
    severity: str = DefectSeverity.NORMAL.value,
) -> tuple[Defect, bool]:
    """
    从执行失败创建缺陷
    
    自动生成标题和指纹
    """
    title = f"[{api_method}] {api_path} - {error_type}"
    
    fingerprint = generate_fingerprint(
        api_path=api_path,
        api_method=api_method,
        error_type=error_type,
        error_message=error_detail,
    )
    
    defect_in = DefectCreate(
        title=title,
        source=DefectSource.EXECUTION.value,
        source_id=str(execution_id),
        api_path=api_path,
        api_method=api_method,
        module=module,
        error_type=error_type,
        request_data=request_data,
        response_data=response_data,
        error_detail=error_detail,
        severity=severity,
        fingerprint=fingerprint,
    )
    
    return create_defect(
        session=session,
        project_id=project_id,
        defect_in=defect_in,
        check_duplicate=True,
    )


def batch_create_defects(
    *,
    session: Session,
    project_id: uuid.UUID,
    defects_in: list[DefectCreate],
    source: str = DefectSource.IMPORT.value,
    source_id: str | None = None,
) -> DefectDedupResult:
    """
    批量创建缺陷
    
    自动去重并返回统计结果
    """
    import logging
    logger = logging.getLogger(__name__)
    
    new_count = 0
    duplicate_count = 0
    error_count = 0
    details = []
    
    for idx, defect_in in enumerate(defects_in):
        try:
            defect_in.source = source
            defect_in.source_id = source_id
            
            defect, is_duplicate = create_defect(
                session=session,
                project_id=project_id,
                defect_in=defect_in,
                check_duplicate=True,
            )
            
            if is_duplicate:
                duplicate_count += 1
                details.append({
                    "title": defect_in.title,
                    "status": "duplicate",
                    "defect_id": str(defect.id),
                    "occurrence_count": defect.occurrence_count,
                })
            else:
                new_count += 1
                details.append({
                    "title": defect_in.title,
                    "status": "new",
                    "defect_id": str(defect.id),
                })
        except Exception as e:
            logger.error(f"批量创建缺陷第 {idx} 条失败: {e}, title={defect_in.title}")
            error_count += 1
            details.append({
                "title": defect_in.title,
                "status": "error",
                "error": str(e),
            })
            try:
                session.rollback()
            except Exception:
                pass
    
    return DefectDedupResult(
        new_count=new_count,
        duplicate_count=duplicate_count,
        error_count=error_count,
        total_count=len(defects_in),
        details=details,
    )


def get_defect(
    *,
    session: Session,
    defect_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> Defect | None:
    """获取单个缺陷"""
    statement = select(Defect).where(Defect.id == defect_id)
    if project_id:
        statement = statement.where(Defect.project_id == project_id)
    return session.exec(statement).first()


def get_defects(
    *,
    session: Session,
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    source: str | None = None,
    severity: str | None = None,
    error_type: str | None = None,
    module: str | None = None,
    api_path: str | None = None,
    keyword: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Defect]:
    """获取缺陷列表"""
    statement = select(Defect).where(Defect.project_id == project_id)
    
    if source:
        statement = statement.where(Defect.source == source)
    if severity:
        statement = statement.where(Defect.severity == severity)
    if error_type:
        statement = statement.where(Defect.error_type == error_type)
    if module:
        statement = statement.where(Defect.module == module)
    if api_path:
        statement = statement.where(Defect.api_path.contains(api_path))
    if keyword:
        statement = statement.where(
            Defect.title.contains(keyword) | Defect.description.contains(keyword)
        )
    if start_date:
        statement = statement.where(Defect.created_at >= start_date)
    if end_date:
        statement = statement.where(Defect.created_at <= end_date)
    
    statement = statement.order_by(Defect.created_at.desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_defects(
    *,
    session: Session,
    project_id: uuid.UUID,
    source: str | None = None,
    severity: str | None = None,
    error_type: str | None = None,
    module: str | None = None,
    api_path: str | None = None,
    keyword: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """统计缺陷数量"""
    statement = select(func.count()).select_from(Defect).where(Defect.project_id == project_id)
    
    if source:
        statement = statement.where(Defect.source == source)
    if severity:
        statement = statement.where(Defect.severity == severity)
    if error_type:
        statement = statement.where(Defect.error_type == error_type)
    if module:
        statement = statement.where(Defect.module == module)
    if api_path:
        statement = statement.where(Defect.api_path.contains(api_path))
    if keyword:
        statement = statement.where(
            Defect.title.contains(keyword) | Defect.description.contains(keyword)
        )
    if start_date:
        statement = statement.where(Defect.created_at >= start_date)
    if end_date:
        statement = statement.where(Defect.created_at <= end_date)
    
    return session.exec(statement).one()


def update_defect(
    *,
    session: Session,
    db_defect: Defect,
    defect_in: DefectUpdate,
) -> Defect:
    """更新缺陷"""
    update_data = defect_in.model_dump(exclude_unset=True)
    
    if "tags" in update_data:
        update_data["tags"] = _dump_tags(update_data["tags"])
    
    db_defect.sqlmodel_update(update_data)
    db_defect.updated_at = get_datetime_china()
    session.add(db_defect)
    session.commit()
    session.refresh(db_defect)
    return db_defect


def delete_defect(
    *,
    session: Session,
    db_defect: Defect,
) -> None:
    """删除缺陷"""
    session.delete(db_defect)
    session.commit()


def get_defect_stats(
    *,
    session: Session,
    project_id: uuid.UUID,
    days: int = 7,
) -> DefectStats:
    """获取缺陷统计"""
    stats = DefectStats()
    
    total_statement = select(func.count()).select_from(Defect).where(
        Defect.project_id == project_id
    )
    stats.total = session.exec(total_statement).one()
    
    source_counts = session.exec(
        select(Defect.source, func.count())
        .where(Defect.project_id == project_id)
        .group_by(Defect.source)
    ).all()
    stats.by_source = {source: count for source, count in source_counts}
    
    severity_counts = session.exec(
        select(Defect.severity, func.count())
        .where(Defect.project_id == project_id)
        .group_by(Defect.severity)
    ).all()
    stats.by_severity = {severity: count for severity, count in severity_counts}
    
    error_type_counts = session.exec(
        select(Defect.error_type, func.count())
        .where(Defect.project_id == project_id)
        .where(Defect.error_type.is_not(None))
        .group_by(Defect.error_type)
    ).all()
    stats.by_error_type = {error_type: count for error_type, count in error_type_counts}
    
    module_counts = session.exec(
        select(Defect.module, func.count())
        .where(Defect.project_id == project_id)
        .where(Defect.module.is_not(None))
        .group_by(Defect.module)
    ).all()
    stats.by_module = {module: count for module, count in module_counts}
    
    recent_date = get_datetime_china() - timedelta(days=days)
    stats.recent_count = session.exec(
        select(func.count()).select_from(Defect).where(
            Defect.project_id == project_id,
            Defect.created_at >= recent_date,
        )
    ).one()
    
    stats.duplicate_count = session.exec(
        select(func.count()).select_from(Defect).where(
            Defect.project_id == project_id,
            Defect.occurrence_count > 1,
        )
    ).one()
    
    return stats


def get_defect_trend(
    *,
    session: Session,
    project_id: uuid.UUID,
    days: int = 30,
) -> list[DefectTrend]:
    """获取缺陷趋势"""
    trends = []
    
    for i in range(days - 1, -1, -1):
        date = (get_datetime_china() - timedelta(days=i)).date()
        next_date = date + timedelta(days=1)
        
        count = session.exec(
            select(func.count()).select_from(Defect).where(
                Defect.project_id == project_id,
                Defect.created_at >= datetime.combine(date, datetime.min.time()),
                Defect.created_at < datetime.combine(next_date, datetime.min.time()),
            )
        ).one()
        
        severity_counts = session.exec(
            select(Defect.severity, func.count())
            .where(Defect.project_id == project_id)
            .where(Defect.created_at >= datetime.combine(date, datetime.min.time()))
            .where(Defect.created_at < datetime.combine(next_date, datetime.min.time()))
            .group_by(Defect.severity)
        ).all()
        
        trends.append(DefectTrend(
            date=date.isoformat(),
            count=count,
            by_severity={severity: cnt for severity, cnt in severity_counts},
        ))
    
    return trends


def get_modules(
    *,
    session: Session,
    project_id: uuid.UUID,
) -> list[str]:
    """获取项目的模块列表"""
    result = session.exec(
        select(Defect.module)
        .where(Defect.project_id == project_id)
        .where(Defect.module.is_not(None))
        .distinct()
    ).all()
    return [m for m in result if m]


def get_api_paths(
    *,
    session: Session,
    project_id: uuid.UUID,
) -> list[str]:
    """获取项目的API路径列表"""
    result = session.exec(
        select(Defect.api_path)
        .where(Defect.project_id == project_id)
        .where(Defect.api_path.is_not(None))
        .distinct()
    ).all()
    return [p for p in result if p]


def merge_defects(
    *,
    session: Session,
    target_defect_id: uuid.UUID,
    source_defect_ids: list[uuid.UUID],
    project_id: uuid.UUID,
) -> Defect:
    """
    合并缺陷
    
    将多个缺陷合并到一个目标缺陷中
    """
    target = get_defect(session=session, defect_id=target_defect_id, project_id=project_id)
    if not target:
        raise ValueError("目标缺陷不存在")
    
    total_occurrence = target.occurrence_count
    
    for source_id in source_defect_ids:
        if source_id == target_defect_id:
            continue
        
        source = get_defect(session=session, defect_id=source_id, project_id=project_id)
        if source:
            total_occurrence += source.occurrence_count
            session.delete(source)
    
    target.occurrence_count = total_occurrence
    target.updated_at = get_datetime_china()
    session.add(target)
    session.commit()
    session.refresh(target)
    
    return target
