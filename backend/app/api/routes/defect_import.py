"""
缺陷导入 API 路由

提供缺陷导入相关接口：
- 上传文件预览
- 确认导入
- 导入记录查询
- 模板下载
"""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from app.api.deps import get_current_active_user, get_db
from app.models import User
from app.models.defect import DefectCreate, DefectSource
from app.models.defect_import import (
    DefectImportRecord,
    ImportPlatform,
    ImportStatus,
    ImportPreview,
    ImportResult,
    DefectImportTemplate,
    ImportRecordPublic,
    ImportRecordsPublic,
    PlatformOption,
    PLATFORM_LABELS,
)
from app.models.base import get_datetime_china
from app.crud.defect import create_defect, batch_create_defects
from app.services.defect_import import (
    DefectImportService,
    detect_platform,
)

router = APIRouter()


@router.post("/upload", response_model=ImportPreview)
async def upload_and_preview(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    file: UploadFile = File(..., description="导入文件"),
    platform: str | None = Query(None, description="平台类型（可选，自动检测）"),
) -> Any:
    """
    上传文件并预览导入数据
    
    - 支持 JSON、Excel 格式
    - 自动检测平台类型（Jira、Tapd、禅道等）
    - 返回预览数据和字段映射
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    file_ext = file.filename.lower().split(".")[-1]
    if file_ext not in ("json", "xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 JSON、Excel 或 CSV 文件")
    
    content = await file.read()
    file_size = len(content)
    
    if not platform:
        platform = detect_platform(file.filename, content[:1024])
    
    try:
        from io import BytesIO
        parsed_platform, raw_data = DefectImportService.parse_file(
            BytesIO(content),
            file.filename,
            platform,
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON 文件格式错误")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")
    
    if not raw_data:
        raise HTTPException(status_code=400, detail="文件中没有有效数据")
    
    preview = DefectImportService.preview_import(raw_data, parsed_platform)
    
    import_record = DefectImportRecord(
        project_id=project_id,
        platform=parsed_platform,
        file_name=file.filename,
        file_size=file_size,
        status=ImportStatus.CONFIRMING.value,
        total_count=preview.total_count,
        parsed_data=json.dumps(raw_data, ensure_ascii=False),
    )
    session.add(import_record)
    session.commit()
    session.refresh(import_record)
    
    preview.preview_data = preview.preview_data[:20]
    
    return ImportPreview(
        record_id=str(import_record.id),
        total_count=preview.total_count,
        new_count=preview.new_count,
        duplicate_count=preview.duplicate_count,
        error_count=preview.error_count,
        preview_data=preview.preview_data,
        field_mapping=preview.field_mapping,
        errors=preview.errors,
    )


@router.post("/confirm/{record_id}", response_model=ImportResult)
def confirm_import(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    record_id: uuid.UUID,
    field_mapping: dict[str, str] | None = Body(default=None, description="字段映射配置"),
) -> Any:
    """
    确认导入
    
    根据预览结果确认导入数据
    """
    record = session.exec(
        select(DefectImportRecord).where(DefectImportRecord.id == record_id)
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="导入记录不存在")
    
    if record.status != ImportStatus.CONFIRMING.value:
        raise HTTPException(status_code=400, detail="导入记录状态不正确")
    
    record.status = ImportStatus.IMPORTING.value
    record.updated_at = get_datetime_china()
    session.add(record)
    session.commit()
    
    try:
        raw_data = json.loads(record.parsed_data) if record.parsed_data else []
        
        if not raw_data:
            record.status = ImportStatus.COMPLETED.value
            record.new_count = 0
            record.duplicate_count = 0
            record.error_count = 0
            record.completed_at = get_datetime_china()
            session.add(record)
            session.commit()
            return ImportResult(
                record_id=str(record.id),
                status=record.status,
                total_count=record.total_count,
                new_count=0,
                duplicate_count=0,
                error_count=0,
                details=[],
            )
        
        # 使用 preview_import 处理全部数据的映射
        from app.services.defect_import import FieldMapper
        from app.models.defect import DefectSeverity
        from app.models.defect_import import SEVERITY_MAPPING
        
        mapper = FieldMapper(record.platform, field_mapping)
        all_defects_data = []
        error_count = 0
        
        for idx, record_data in enumerate(raw_data):
            try:
                mapped = mapper.map_record(record_data)
                
                title = mapped.get("title") or mapped.get("summary") or f"导入记录 {idx + 1}"
                
                severity = mapped.get("severity", DefectSeverity.NORMAL.value)
                if isinstance(severity, str):
                    severity = SEVERITY_MAPPING.get(
                        severity.strip(),
                        SEVERITY_MAPPING.get(severity.lower(), DefectSeverity.NORMAL.value)
                    )
                if isinstance(severity, int):
                    severity = SEVERITY_MAPPING.get(str(severity), DefectSeverity.NORMAL.value)
                
                tags = mapped.get("tags")
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.replace("，", ",").split(",") if t.strip()]
                elif tags is None:
                    tags = []
                
                description = mapped.get("description", "")
                if description and len(str(description)) > 5000:
                    description = str(description)[:5000] + "..."
                
                # 获取外部ID (Bug编号)
                external_id = mapped.get("external_id") or mapped.get("source_id", "")
                
                defect_create_data = {
                    "title": str(title)[:200],
                    "description": str(description) if description else None,
                    "source": DefectSource.IMPORT.value,
                    "source_id": str(external_id)[:100] if external_id else None,
                    "module": mapped.get("module"),
                    "error_type": mapped.get("error_type"),
                    "severity": severity,
                    "tags": tags,
                }
                all_defects_data.append(defect_create_data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"映射记录 {idx} 失败: {e}")
                error_count += 1
        
        defects_to_create = []
        for data in all_defects_data:
            try:
                defects_to_create.append(DefectCreate(**data))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"构造 DefectCreate 失败: {e}, data={data}")
                error_count += 1
        
        if not defects_to_create:
            record.status = ImportStatus.COMPLETED.value
            record.new_count = 0
            record.duplicate_count = 0
            record.error_count = error_count
            record.completed_at = get_datetime_china()
            session.add(record)
            session.commit()
            return ImportResult(
                record_id=str(record.id),
                status=record.status,
                total_count=record.total_count,
                new_count=0,
                duplicate_count=0,
                error_count=error_count,
                details=[],
            )
        
        project_id = record.project_id
        record_id_str = str(record.id)
        total_count = record.total_count
        
        result = batch_create_defects(
            session=session,
            project_id=project_id,
            defects_in=defects_to_create,
            source=DefectSource.IMPORT.value,
            source_id=record_id_str,
        )
        
        # batch_create_defects 中可能发生过 rollback，record 对象可能已 detached
        # 重新查询确保对象有效
        record = session.exec(
            select(DefectImportRecord).where(DefectImportRecord.id == record_id)
        ).first()
        if not record:
            raise HTTPException(status_code=500, detail="导入记录丢失")
        
        record.status = ImportStatus.COMPLETED.value
        record.new_count = result.new_count
        record.duplicate_count = result.duplicate_count
        record.error_count = result.error_count + error_count
        record.completed_at = get_datetime_china()
        session.add(record)
        session.commit()
        
        return ImportResult(
            record_id=str(record.id),
            status=record.status,
            total_count=total_count,
            new_count=record.new_count,
            duplicate_count=record.duplicate_count,
            error_count=record.error_count,
            details=result.details,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"确认导入失败 record_id={record_id}: {e}")
        traceback.print_exc()
        
        try:
            session.rollback()
        except Exception:
            pass
        
        try:
            record = session.exec(
                select(DefectImportRecord).where(DefectImportRecord.id == record_id)
            ).first()
            if record:
                record.status = ImportStatus.FAILED.value
                record.error_detail = str(e)[:500]
                record.updated_at = get_datetime_china()
                session.add(record)
                session.commit()
        except Exception as update_err:
            logger.error(f"更新导入记录状态失败: {update_err}")
        
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/records", response_model=ImportRecordsPublic)
def get_import_records(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID = Query(..., description="项目ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """获取导入记录列表"""
    from sqlmodel import func
    
    count_query = select(func.count()).select_from(DefectImportRecord).where(
        DefectImportRecord.project_id == project_id
    )
    total_count = session.exec(count_query).one()
    
    records = session.exec(
        select(DefectImportRecord)
        .where(DefectImportRecord.project_id == project_id)
        .order_by(DefectImportRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    
    data = [
        ImportRecordPublic(
            id=str(r.id),
            platform=r.platform,
            platform_label=PLATFORM_LABELS.get(ImportPlatform(r.platform), r.platform),
            file_name=r.file_name,
            file_size=r.file_size,
            status=r.status,
            total_count=r.total_count,
            new_count=r.new_count,
            duplicate_count=r.duplicate_count,
            error_count=r.error_count,
            created_at=r.created_at.isoformat() if r.created_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
        for r in records
    ]
    
    return ImportRecordsPublic(data=data, count=total_count)


@router.get("/template/{platform}", response_model=DefectImportTemplate)
def get_import_template(
    *,
    platform: str,
) -> Any:
    """获取导入模板"""
    templates = {
        ImportPlatform.JSON.value: DefectImportTemplate(
            platform=ImportPlatform.JSON.value,
            fields=[
                {"name": "title", "type": "string", "required": True, "description": "缺陷标题"},
                {"name": "description", "type": "string", "required": False, "description": "缺陷描述"},
                {"name": "severity", "type": "string", "required": False, "description": "严重程度: critical/major/normal/minor/suggestion"},
                {"name": "api_path", "type": "string", "required": False, "description": "API路径"},
                {"name": "api_method", "type": "string", "required": False, "description": "HTTP方法: GET/POST/PUT/DELETE"},
                {"name": "module", "type": "string", "required": False, "description": "所属模块"},
                {"name": "error_type", "type": "string", "required": False, "description": "错误类型"},
                {"name": "tags", "type": "array", "required": False, "description": "标签列表"},
            ],
            sample_data=[
                {
                    "title": "登录接口返回500错误",
                    "description": "调用登录接口时返回500内部服务器错误",
                    "severity": "major",
                    "api_path": "/api/v1/auth/login",
                    "api_method": "POST",
                    "module": "认证模块",
                    "error_type": "http_5xx",
                    "tags": ["登录", "认证"],
                }
            ],
        ),
        ImportPlatform.EXCEL.value: DefectImportTemplate(
            platform=ImportPlatform.EXCEL.value,
            fields=[
                {"name": "标题", "type": "string", "required": True, "description": "缺陷标题"},
                {"name": "描述", "type": "string", "required": False, "description": "缺陷描述"},
                {"name": "严重程度", "type": "string", "required": False, "description": "致命/严重/一般/轻微/建议"},
                {"name": "API路径", "type": "string", "required": False, "description": "API路径"},
                {"name": "请求方法", "type": "string", "required": False, "description": "GET/POST/PUT/DELETE"},
                {"name": "模块", "type": "string", "required": False, "description": "所属模块"},
                {"name": "错误类型", "type": "string", "required": False, "description": "错误类型"},
                {"name": "标签", "type": "string", "required": False, "description": "标签，逗号分隔"},
            ],
            sample_data=[
                {
                    "标题": "登录接口返回500错误",
                    "描述": "调用登录接口时返回500内部服务器错误",
                    "严重程度": "严重",
                    "API路径": "/api/v1/auth/login",
                    "请求方法": "POST",
                    "模块": "认证模块",
                    "错误类型": "服务端错误",
                    "标签": "登录,认证",
                }
            ],
        ),
        ImportPlatform.JIRA.value: DefectImportTemplate(
            platform=ImportPlatform.JIRA.value,
            fields=[
                {"name": "summary", "type": "string", "required": True, "description": "Jira 标题"},
                {"name": "description", "type": "string", "required": False, "description": "Jira 描述"},
                {"name": "priority", "type": "string", "required": False, "description": "Jira 优先级"},
                {"name": "labels", "type": "array", "required": False, "description": "Jira 标签"},
                {"name": "components", "type": "array", "required": False, "description": "Jira 组件"},
            ],
            sample_data=[
                {
                    "id": "10001",
                    "key": "PROJ-123",
                    "fields": {
                        "summary": "登录接口返回500错误",
                        "description": "调用登录接口时返回500内部服务器错误",
                        "priority": {"name": "High"},
                        "labels": ["登录", "认证"],
                        "components": [{"name": "认证模块"}],
                    }
                }
            ],
        ),
    }
    
    template = templates.get(platform)
    if not template:
        raise HTTPException(status_code=404, detail=f"不支持的平台: {platform}")
    
    return template


@router.get("/platforms", response_model=list[PlatformOption])
def get_supported_platforms() -> Any:
    """获取支持的平台列表"""
    return [
        PlatformOption(value=p.value, label=label)
        for p, label in PLATFORM_LABELS.items()
    ]
