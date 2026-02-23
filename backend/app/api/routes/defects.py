"""
缺陷管理 API 路由

核心接口：
- CRUD 操作
- 批量导入
- 统计分析
- 趋势分析
- 缺陷合并
"""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session

from app.api.deps import get_current_active_user, get_db
from app.crud.defect import (
    create_defect,
    create_defect_from_execution,
    batch_create_defects,
    get_defect,
    get_defects,
    count_defects,
    update_defect,
    delete_defect,
    get_defect_stats,
    get_defect_trend,
    get_modules,
    get_api_paths,
    merge_defects,
)
from app.crud.project import get_project
from app.models.defect import (
    Defect,
    DefectCreate,
    DefectUpdate,
    DefectPublic,
    DefectsPublic,
    DefectStats,
    DefectTrend,
    DefectBatchCreate,
    DefectDedupResult,
    DefectSource,
    DefectSeverity,
    ErrorType,
    SOURCE_LABELS,
    SEVERITY_LABELS,
    ERROR_TYPE_LABELS,
)
from app.models import Message
from app.models.user import User

router = APIRouter()


def _defect_to_public(defect: Defect) -> DefectPublic:
    """将 Defect 模型转换为 DefectPublic"""
    tags = None
    if defect.tags:
        try:
            tags = json.loads(defect.tags)
        except json.JSONDecodeError:
            tags = None
    
    return DefectPublic(
        id=defect.id,
        project_id=defect.project_id,
        title=defect.title,
        description=defect.description,
        source=defect.source,
        source_id=defect.source_id,
        api_path=defect.api_path,
        api_method=defect.api_method,
        module=defect.module,
        error_type=defect.error_type,
        request_data=defect.request_data,
        response_data=defect.response_data,
        error_detail=defect.error_detail,
        severity=defect.severity,
        tags=tags,
        fingerprint=defect.fingerprint,
        occurrence_count=defect.occurrence_count,
        ai_analysis=defect.ai_analysis,
        ai_suggestion=defect.ai_suggestion,
        created_at=defect.created_at,
        updated_at=defect.updated_at,
    )


@router.get("/stats", response_model=DefectStats)
def get_stats(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
) -> Any:
    """获取缺陷统计"""
    project = get_project(session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return get_defect_stats(session=session, project_id=project_id, days=days)


@router.get("/trend", response_model=list[DefectTrend])
def get_trend(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    days: int = Query(30, ge=7, le=90, description="趋势天数"),
) -> Any:
    """获取缺陷趋势"""
    project = get_project(session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return get_defect_trend(session=session, project_id=project_id, days=days)


@router.get("/modules", response_model=list[str])
def get_project_modules(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
) -> Any:
    """获取项目的模块列表"""
    return get_modules(session=session, project_id=project_id)


@router.get("/api-paths", response_model=list[str])
def get_project_api_paths(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
) -> Any:
    """获取项目的API路径列表"""
    return get_api_paths(session=session, project_id=project_id)


@router.get("/enums", response_model=dict)
def get_enums(
    *,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取枚举值"""
    return {
        "source": {s.value: SOURCE_LABELS[s] for s in DefectSource},
        "severity": {s.value: SEVERITY_LABELS[s] for s in DefectSeverity},
        "error_type": {t.value: ERROR_TYPE_LABELS[t] for t in ErrorType},
    }


@router.get("/", response_model=DefectsPublic)
def list_defects(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    source: str | None = Query(None, description="来源筛选"),
    severity: str | None = Query(None, description="严重程度筛选"),
    error_type: str | None = Query(None, description="错误类型筛选"),
    module: str | None = Query(None, description="模块筛选"),
    api_path: str | None = Query(None, description="API路径筛选"),
    keyword: str | None = Query(None, description="关键词搜索"),
    start_date: datetime | None = Query(None, description="开始日期"),
    end_date: datetime | None = Query(None, description="结束日期"),
) -> Any:
    """获取缺陷列表"""
    project = get_project(session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    defects = get_defects(
        session=session,
        project_id=project_id,
        skip=skip,
        limit=limit,
        source=source,
        severity=severity,
        error_type=error_type,
        module=module,
        api_path=api_path,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
    )
    count = count_defects(
        session=session,
        project_id=project_id,
        source=source,
        severity=severity,
        error_type=error_type,
        module=module,
        api_path=api_path,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
    )

    return DefectsPublic(data=[_defect_to_public(d) for d in defects], count=count)


@router.post("/", response_model=DefectPublic)
def create_new_defect(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    defect_in: DefectCreate,
    check_duplicate: bool = Query(True, description="是否检查重复"),
) -> Any:
    """创建缺陷"""
    project = get_project(session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    defect, is_duplicate = create_defect(
        session=session,
        project_id=project_id,
        defect_in=defect_in,
        check_duplicate=check_duplicate,
    )
    return _defect_to_public(defect)


@router.post("/batch", response_model=DefectDedupResult)
def batch_create(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    batch_in: DefectBatchCreate,
) -> Any:
    """批量创建缺陷（导入）"""
    project = get_project(session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return batch_create_defects(
        session=session,
        project_id=project_id,
        defects_in=batch_in.defects,
        source=batch_in.source,
        source_id=batch_in.source_id,
    )


@router.post("/from-execution", response_model=DefectPublic)
def create_from_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    execution_id: uuid.UUID = Query(..., description="执行ID"),
    api_path: str = Query(..., description="API路径"),
    api_method: str = Query(..., description="HTTP方法"),
    error_type: str = Query(..., description="错误类型"),
    error_detail: str = Query(..., description="错误详情"),
    request_data: str | None = Query(None, description="请求数据"),
    response_data: str | None = Query(None, description="响应数据"),
    module: str | None = Query(None, description="模块"),
    severity: str = Query(DefectSeverity.NORMAL.value, description="严重程度"),
) -> Any:
    """从执行失败创建缺陷"""
    project = get_project(session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    defect, _ = create_defect_from_execution(
        session=session,
        project_id=project_id,
        execution_id=execution_id,
        api_path=api_path,
        api_method=api_method,
        error_type=error_type,
        error_detail=error_detail,
        request_data=request_data,
        response_data=response_data,
        module=module,
        severity=severity,
    )
    return _defect_to_public(defect)


@router.get("/{defect_id}", response_model=DefectPublic)
def get_defect_detail(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    defect_id: uuid.UUID,
) -> Any:
    """获取缺陷详情"""
    defect = get_defect(session=session, defect_id=defect_id, project_id=project_id)
    if not defect:
        raise HTTPException(status_code=404, detail="缺陷不存在")
    return _defect_to_public(defect)


@router.put("/{defect_id}", response_model=DefectPublic)
def update_defect_info(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    defect_id: uuid.UUID,
    defect_in: DefectUpdate,
) -> Any:
    """更新缺陷"""
    defect = get_defect(session=session, defect_id=defect_id, project_id=project_id)
    if not defect:
        raise HTTPException(status_code=404, detail="缺陷不存在")

    defect = update_defect(session=session, db_defect=defect, defect_in=defect_in)
    return _defect_to_public(defect)


@router.delete("/{defect_id}", response_model=Message)
def delete_defect_by_id(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    defect_id: uuid.UUID,
) -> Any:
    """删除缺陷"""
    defect = get_defect(session=session, defect_id=defect_id, project_id=project_id)
    if not defect:
        raise HTTPException(status_code=404, detail="缺陷不存在")

    delete_defect(session=session, db_defect=defect)
    return Message(message="删除成功")


@router.post("/merge", response_model=DefectPublic)
def merge_defects_api(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    target_defect_id: uuid.UUID = Body(..., description="目标缺陷ID"),
    source_defect_ids: list[uuid.UUID] = Body(..., description="要合并的缺陷ID列表"),
) -> Any:
    """合并缺陷"""
    try:
        defect = merge_defects(
            session=session,
            target_defect_id=target_defect_id,
            source_defect_ids=source_defect_ids,
            project_id=project_id,
        )
        return _defect_to_public(defect)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/batch", response_model=Message)
def batch_delete_defects(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    defect_ids: list[uuid.UUID] = Body(..., description="要删除的缺陷ID列表"),
) -> Any:
    """批量删除缺陷"""
    deleted_count = 0
    for defect_id in defect_ids:
        defect = get_defect(session=session, defect_id=defect_id, project_id=project_id)
        if defect:
            delete_defect(session=session, db_defect=defect)
            deleted_count += 1

    return Message(message=f"成功删除 {deleted_count} 个缺陷")
