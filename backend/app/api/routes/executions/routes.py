# 测试执行 API 路由
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models import Message
from app.models.execution import (
    TestExecution,
    TestExecutionCreate,
    TestExecutionUpdate,
    TestExecutionPublic,
    TestExecutionsPublic,
    ExecutionStats,
)
from app.crud.execution import (
    create_execution,
    get_execution,
    get_executions,
    count_executions,
    update_execution,
    delete_execution,
    get_execution_stats,
)
from app.crud.project import get_project
from app.services.apifox import apifox_service, ApifoxCliError
from app.services.notification_trigger import trigger_execution_notification, trigger_threshold_alert
from app.services.audit_log import create_audit_log
from app.models.audit_log import AuditStatus


class ExecutionRunRequest(BaseModel):
    project_id: Optional[str] = None
    collection_id: str
    collection_type: Optional[str] = "test-suite"
    environment: Optional[str] = None
    access_token: Optional[str] = None


router = APIRouter(prefix="/executions", tags=["executions"])


class ReportNoteUpsert(BaseModel):
    note_type: str
    note_key: str
    content: str
    tags: list[str] = []


@router.get("/stats", response_model=ExecutionStats)
def read_execution_stats(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取测试执行统计数据
    """
    return get_execution_stats(session=session)


@router.get("/", response_model=TestExecutionsPublic)
def read_executions(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    collection_id: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Any:
    """
    获取测试执行记录列表（支持分页和筛选）
    
    - **skip**: 跳过记录数（分页偏移）
    - **limit**: 返回记录数（默认 20）
    - **status**: 按状态筛选（pending/running/completed/failed）
    - **project_id**: 按项目ID筛选
    - **project_name**: 按项目名称模糊搜索
    - **start_date**: 开始时间（ISO 格式）
    - **end_date**: 结束时间（ISO 格式）
    """
    executions = get_executions(
        session=session,
        skip=skip,
        limit=limit,
        status=status,
        collection_id=collection_id,
        project_id=project_id,
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
    )
    total_count = count_executions(
        session=session,
        status=status,
        collection_id=collection_id,
        project_id=project_id,
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
    )
    return TestExecutionsPublic(data=executions, count=total_count)


@router.post("/", response_model=TestExecutionPublic)
def create_new_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    execution_in: TestExecutionCreate,
    request: Request,
) -> Any:
    """
    创建新的测试执行
    
    - **apifox_collection_id**: Apifox 测试集合 ID
    - **project_name**: 项目名称（可选）
    - **environment**: 执行环境（可选）
    """
    execution = create_execution(session=session, execution_in=execution_in)
    create_audit_log(
        session=session,
        action="create",
        resource_type="execution",
        resource_id=str(execution.id),
        resource_name=execution.project_name,
        status=AuditStatus.SUCCESS,
        request=request,
        actor=current_user,
        after=execution,
    )
    return execution


@router.get("/{execution_id}", response_model=TestExecutionPublic)
def read_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    execution_id: uuid.UUID,
) -> Any:
    """
    通过 ID 获取测试执行详情
    """
    execution = get_execution(session=session, execution_id=execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return execution


@router.put("/{execution_id}", response_model=TestExecutionPublic)
def update_existing_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    execution_id: uuid.UUID,
    execution_in: TestExecutionUpdate,
    request: Request,
) -> Any:
    """
    更新测试执行信息
    """
    execution = get_execution(session=session, execution_id=execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    before = execution.model_dump()
    execution = update_execution(session=session, db_execution=execution, execution_in=execution_in)
    update_dict = execution_in.model_dump(exclude_unset=True)
    diff_summary = ",".join(sorted(update_dict.keys())) if update_dict else None
    create_audit_log(
        session=session,
        action="update",
        resource_type="execution",
        resource_id=str(execution.id),
        resource_name=execution.project_name,
        status=AuditStatus.SUCCESS,
        request=request,
        actor=current_user,
        before=before,
        after=execution,
        diff_summary=diff_summary,
    )
    return execution


@router.delete("/{execution_id}", response_model=Message)
def delete_existing_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    execution_id: uuid.UUID,
    request: Request,
) -> Any:
    """
    删除测试执行记录
    """
    execution = get_execution(session=session, execution_id=execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    before = execution.model_dump()
    delete_execution(session=session, db_execution=execution)
    create_audit_log(
        session=session,
        action="delete",
        resource_type="execution",
        resource_id=str(execution_id),
        resource_name=execution.project_name,
        status=AuditStatus.SUCCESS,
        request=request,
        actor=current_user,
        before=before,
    )
    return Message(message="执行记录已删除")


@router.post("/run", response_model=TestExecutionPublic)
async def create_and_run_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    request: Request,
    body: ExecutionRunRequest,
) -> Any:
    """
    创建并执行测试（一步完成）
    
    - **project_id**: 项目 ID（可选）
    - **collection_id**: Apifox 测试集合 ID
    - **collection_type**: 集合类型（test-suite/test-scenario）
    - **environment**: 执行环境（可选）
    - **access_token**: Apifox Access Token（可选）
    """
    if not body.collection_id:
        raise HTTPException(status_code=400, detail="缺少 collection_id 参数")
    
    project_name = None
    if body.project_id:
        project = get_project(session=session, project_id=body.project_id)
        if project:
            project_name = project.name
    
    execution_in = TestExecutionCreate(
        project_id=uuid.UUID(body.project_id) if body.project_id else None,
        apifox_collection_id=body.collection_id,
        collection_type=body.collection_type or "test-suite",
        environment=body.environment,
        project_name=project_name,
    )
    
    execution = create_execution(session=session, execution_in=execution_in)
    
    try:
        actual_collection_id = body.collection_id
        actual_collection_type = body.collection_type or "test-suite"
        
        if actual_collection_type == "test-scenario" and actual_collection_id.startswith("ts-"):
            actual_collection_id = actual_collection_id[3:]
        elif actual_collection_type == "test-scenario-folder" and actual_collection_id.startswith("tf-"):
            actual_collection_id = actual_collection_id[3:]
        elif actual_collection_type == "test-suite" and actual_collection_id.startswith("suite-"):
            actual_collection_id = actual_collection_id[6:]
        
        execution = await apifox_service.execute_and_save(
            session=session,
            execution=execution,
            collection_id=actual_collection_id,
            environment_id=body.environment,
            collection_type=actual_collection_type,
            access_token=body.access_token,
        )
        create_audit_log(
            session=session,
            action="run",
            resource_type="execution",
            resource_id=str(execution.id),
            resource_name=execution.project_name,
            status=AuditStatus.SUCCESS,
            request=request,
            actor=current_user,
            after=execution,
        )
        
        await trigger_execution_notification(
            session=session,
            execution=execution,
            project_name=project_name,
        )
        
        await trigger_threshold_alert(
            session=session,
            execution=execution,
            project_name=project_name,
        )
        
        return execution
    except ApifoxCliError as e:
        create_audit_log(
            session=session,
            action="run",
            resource_type="execution",
            resource_id=str(execution.id),
            resource_name=execution.project_name if execution else None,
            status=AuditStatus.FAILURE,
            request=request,
            actor=current_user,
            error_message=f"CLI 执行失败: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=f"CLI 执行失败: {str(e)}")
    except Exception as e:
        create_audit_log(
            session=session,
            action="run",
            resource_type="execution",
            resource_id=str(execution.id),
            resource_name=execution.project_name if execution else None,
            status=AuditStatus.FAILURE,
            request=request,
            actor=current_user,
            error_message=f"执行异常: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=f"执行异常: {str(e)}")


@router.post("/{execution_id}/run", response_model=TestExecutionPublic)
async def run_execution(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    execution_id: uuid.UUID,
    request: Request,
) -> Any:
    """
    执行测试
    
    - 调用 Apifox CLI 执行测试集合
    - 实时更新执行状态和结果
    - 报告保存到 MongoDB
    """
    execution = get_execution(session=session, execution_id=execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 检查是否正在执行中
    if execution.status == "running":
        raise HTTPException(status_code=400, detail="该测试正在执行中")
    
    try:
        # 调用 Apifox CLI 执行测试
        # 优先使用 execution.collection_type 字段，如果没有则根据 collection_id 前缀判断
        # ts- 前缀表示 test-scenario，tf- 前缀表示 test-scenario-folder，suite- 前缀表示 test-suite
        collection_id = execution.apifox_collection_id
        collection_type = execution.collection_type or ""
        if collection_type:
            if collection_type == "test-scenario" and collection_id.startswith("ts-"):
                collection_id = collection_id[3:]
            elif (
                collection_type == "test-scenario-folder"
                and collection_id.startswith("tf-")
            ):
                collection_id = collection_id[3:]
            elif collection_type == "test-suite" and collection_id.startswith("suite-"):
                collection_id = collection_id[6:]
        elif collection_id.startswith("ts-"):
            collection_type = "test-scenario"
            collection_id = collection_id[3:]
        elif collection_id.startswith("tf-"):
            collection_type = "test-scenario-folder"
            collection_id = collection_id[3:]
        elif collection_id.startswith("suite-"):
            collection_type = "test-suite"
            collection_id = collection_id[6:]
        else:
            collection_type = "test-suite"
        
        execution = await apifox_service.execute_and_save(
            session=session,
            execution=execution,
            collection_id=collection_id,
            environment_id=execution.environment,
            collection_type=collection_type,
        )
        create_audit_log(
            session=session,
            action="run",
            resource_type="execution",
            resource_id=str(execution_id),
            resource_name=execution.project_name,
            status=AuditStatus.SUCCESS,
            request=request,
            actor=current_user,
            after=execution,
        )
        return execution
    except ApifoxCliError as e:
        create_audit_log(
            session=session,
            action="run",
            resource_type="execution",
            resource_id=str(execution_id),
            resource_name=execution.project_name if execution else None,
            status=AuditStatus.FAILURE,
            request=request,
            actor=current_user,
            error_message=f"CLI 执行失败: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=f"CLI 执行失败: {str(e)}")
    except Exception as e:
        create_audit_log(
            session=session,
            action="run",
            resource_type="execution",
            resource_id=str(execution_id),
            resource_name=execution.project_name if execution else None,
            status=AuditStatus.FAILURE,
            request=request,
            actor=current_user,
            error_message=f"执行异常: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=f"执行异常: {str(e)}")


@router.get("/{execution_id}/report", response_model=dict[str, Any])
async def get_execution_report(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    execution_id: uuid.UUID,
) -> Any:
    """
    获取测试执行的详细报告
    
    优先从 MongoDB 获取，如果没有则返回 MySQL 中的数据
    """
    from app.services.mongodb_report import MongoDBReportService
    
    execution = get_execution(session=session, execution_id=execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 优先从 MongoDB 获取
    if execution.has_mongodb_report and execution.mongo_report_id:
        report = await MongoDBReportService.get_report_by_id(execution.mongo_report_id)
        if report:
            return report
    
    # 回退到 MySQL
    if execution.report_json:
        return {"report": execution.report_json}
    
    raise HTTPException(status_code=404, detail="报告不存在")


@router.get("/analytics/trend", response_model=dict[str, Any])
async def get_trend_analysis_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 30,
) -> Any:
    """
    获取测试执行趋势分析
    
    - **collection_id**: 可选，按集合筛选
    - **project_id**: 可选，按项目筛选
    - **days**: 查询天数（默认 30 天）
    """
    from app.services.mongodb_report import MongoDBReportService
    
    try:
        trend_data = await MongoDBReportService.get_trend_analysis(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
        )
        return {"data": trend_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/failed-apis", response_model=dict[str, Any])
async def get_failed_apis_analysis_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 7,
    limit: int = 10,
) -> Any:
    """
    获取高频失败 API 分析
    
    - **collection_id**: 可选，按集合筛选
    - **project_id**: 可选，按项目筛选
    - **days**: 查询天数（默认 7 天）
    - **limit**: 返回数量（默认 10）
    """
    from app.services.mongodb_report import MongoDBReportService
    
    try:
        failed_apis = await MongoDBReportService.get_top_failed_apis(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
            limit=limit,
        )
        return {"data": failed_apis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/performance", response_model=dict[str, Any])
async def get_performance_analysis_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 7,
) -> Any:
    """
    获取性能统计分析
    
    - **collection_id**: 可选，按集合筛选
    - **project_id**: 可选，按项目筛选
    - **days**: 查询天数（默认 7 天）
    """
    from app.services.mongodb_report import MongoDBReportService
    
    try:
        stats = await MongoDBReportService.get_performance_stats(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
        )
        return {"data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/overview", response_model=dict[str, Any])
async def get_overview_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 30,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        data = await MongoDBReportService.get_overview(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/slow-apis", response_model=dict[str, Any])
async def get_slow_apis_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 30,
    limit: int = 10,
    baseline_execution_id: str | None = None,
    target_execution_id: str | None = None,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        data = await MongoDBReportService.get_slow_apis(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
            limit=limit,
            baseline_execution_id=baseline_execution_id,
            target_execution_id=target_execution_id,
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/failure-signatures", response_model=dict[str, Any])
async def get_failure_signatures_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 30,
    limit: int = 10,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        data = await MongoDBReportService.get_failure_signatures(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
            limit=limit,
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/collections", response_model=dict[str, Any])
async def get_collections_api(
    *,
    current_user: User = Depends(get_current_active_user),
    project_id: str | None = None,
    days: int = 365,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        data = await MongoDBReportService.get_collections(
            project_id=project_id,
            days=days,
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")


@router.get("/analytics/flaky", response_model=dict[str, Any])
async def get_flaky_api(
    *,
    current_user: User = Depends(get_current_active_user),
    collection_id: str | None = None,
    project_id: str | None = None,
    days: int = 30,
    limit: int = 10,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        data = await MongoDBReportService.get_flaky_endpoints(
            collection_id=collection_id,
            project_id=project_id,
            days=days,
            limit=limit,
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analytics/note", response_model=dict[str, Any])
async def get_note_api(
    *,
    current_user: User = Depends(get_current_active_user),
    note_type: str,
    note_key: str,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        note = await MongoDBReportService.get_note(note_type=note_type, note_key=note_key)
        return {"data": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")


@router.put("/analytics/note", response_model=dict[str, Any])
async def upsert_note_api(
    *,
    current_user: User = Depends(get_current_active_user),
    payload: ReportNoteUpsert,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        note = await MongoDBReportService.upsert_note(
            note_type=payload.note_type,
            note_key=payload.note_key,
            content=payload.content,
            tags=payload.tags,
            updated_by=str(current_user.id),
        )
        return {"data": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get("/analytics/compare", response_model=dict[str, Any])
async def compare_executions_api(
    *,
    current_user: User = Depends(get_current_active_user),
    left: str,
    right: str,
) -> Any:
    from app.services.mongodb_report import MongoDBReportService

    try:
        left_summary_doc = await MongoDBReportService.get_summary_by_execution_id(left)
        right_summary_doc = await MongoDBReportService.get_summary_by_execution_id(right)
        if not left_summary_doc or not right_summary_doc:
            raise HTTPException(status_code=404, detail="执行报告不存在")

        left_failures = await MongoDBReportService.get_failure_fingerprints(left)
        right_failures = await MongoDBReportService.get_failure_fingerprints(right)

        new_keys = sorted(set(right_failures.keys()) - set(left_failures.keys()))
        resolved_keys = sorted(set(left_failures.keys()) - set(right_failures.keys()))

        def _shape_failure(fp: str, src: dict) -> dict:
            return {
                "fingerprint": fp,
                "name": src.get("name"),
                "api_path": src.get("api_path"),
                "api_method": src.get("api_method"),
                "response_status": src.get("response_status"),
                "error": src.get("error"),
            }

        new_failures = [_shape_failure(k, right_failures[k]) for k in new_keys[:50]]
        resolved_failures = [_shape_failure(k, left_failures[k]) for k in resolved_keys[:50]]

        lsum = left_summary_doc.get("summary") or {}
        rsum = right_summary_doc.get("summary") or {}
        lreq = left_summary_doc.get("request_stats") or {}
        rreq = right_summary_doc.get("request_stats") or {}

        left_profile = await MongoDBReportService.get_execution_request_profile(left)
        right_profile = await MongoDBReportService.get_execution_request_profile(right)

        slow_compare = await MongoDBReportService.get_slow_apis(
            limit=20,
            baseline_execution_id=left,
            target_execution_id=right,
        )

        diff = {
            "new_failures_count": len(new_keys),
            "resolved_failures_count": len(resolved_keys),
            "new_failures": new_failures,
            "resolved_failures": resolved_failures,
            "metrics": {
                "tests_total_left": lsum.get("tests_total"),
                "tests_total_right": rsum.get("tests_total"),
                "tests_failed_left": lsum.get("tests_failed"),
                "tests_failed_right": rsum.get("tests_failed"),
                "response_time_avg_left": lsum.get("response_time_avg"),
                "response_time_avg_right": rsum.get("response_time_avg"),
                "response_time_max_left": lsum.get("response_time_max"),
                "response_time_max_right": rsum.get("response_time_max"),
            },
            "request_stats": {
                "left": lreq,
                "right": rreq,
            },
            "slow_compare": slow_compare,
        }

        return {
            "left": left_summary_doc,
            "right": right_summary_doc,
            "left_profile": left_profile,
            "right_profile": right_profile,
            "diff": diff,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对比失败: {str(e)}")
