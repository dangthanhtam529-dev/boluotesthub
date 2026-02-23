from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session
from typing import Any
import uuid

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User,
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectPublic,
    ProjectsPublic,
    Collection,
    CollectionCreate,
    CollectionUpdate,
    CollectionPublic,
    CollectionsPublic,
    ProjectStats,
    Message,
)
from app.crud.project import (
    create_project,
    get_project,
    get_projects,
    count_projects,
    update_project,
    delete_project,
    get_project_stats,
    create_collection,
    get_collection,
    get_collections_by_project,
    update_collection,
    delete_collection,
    get_collection_by_apifox_id,
)
from app.services.apifox import apifox_service

router = APIRouter()


@router.get("/", response_model=ProjectsPublic)
async def list_projects(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
) -> Any:
    projects = get_projects(
        session=session,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    count = count_projects(session=session, is_active=is_active)
    
    result = []
    for p in projects:
        stats = get_project_stats(session=session, project_id=str(p.id))
        result.append(
            ProjectPublic(
                id=p.id,
                name=p.name,
                description=p.description,
                apifox_project_id=p.apifox_project_id,
                owner_id=p.owner_id,
                is_active=p.is_active,
                last_sync_at=p.last_sync_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
                collection_count=stats.total_collections,
                execution_count=stats.total_executions,
            )
        )
    
    return ProjectsPublic(data=result, count=count)


@router.post("/", response_model=ProjectPublic)
async def create_new_project(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_in: ProjectCreate,
) -> Any:
    project = create_project(
        session=session,
        project_in=project_in,
        owner_id=str(current_user.id),
    )
    return ProjectPublic(
        id=project.id,
        name=project.name,
        description=project.description,
        apifox_project_id=project.apifox_project_id,
        owner_id=project.owner_id,
        is_active=project.is_active,
        last_sync_at=project.last_sync_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/{project_id}", response_model=ProjectPublic)
async def get_project_detail(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    stats = get_project_stats(session=session, project_id=str(project_id))
    return ProjectPublic(
        id=project.id,
        name=project.name,
        description=project.description,
        apifox_project_id=project.apifox_project_id,
        owner_id=project.owner_id,
        is_active=project.is_active,
        last_sync_at=project.last_sync_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        collection_count=stats.total_collections,
        execution_count=stats.total_executions,
    )


@router.put("/{project_id}", response_model=ProjectPublic)
async def update_project_detail(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    project_in: ProjectUpdate,
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    project = update_project(session=session, db_project=project, project_in=project_in)
    return ProjectPublic(
        id=project.id,
        name=project.name,
        description=project.description,
        apifox_project_id=project.apifox_project_id,
        owner_id=project.owner_id,
        is_active=project.is_active,
        last_sync_at=project.last_sync_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}", response_model=Message)
async def delete_project_by_id(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    delete_project(session=session, project_id=str(project_id))
    return Message(message="项目已删除")


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_statistics(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return get_project_stats(session=session, project_id=str(project_id))


@router.get("/{project_id}/apifox-info", response_model=dict[str, Any])
async def get_apifox_project_info(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    access_token: str | None = Query(None, description="Apifox Access Token"),
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if not project.apifox_project_id:
        return {"data": None, "message": "项目未关联 Apifox 项目"}
    
    try:
        info = await apifox_service.get_project_info(
            project_id=project.apifox_project_id.strip() if project.apifox_project_id else "",
            access_token=access_token,
        )
        if info:
            return {
                "data": {
                    "id": info.get("id"),
                    "name": info.get("name"),
                    "description": info.get("description"),
                    "type": info.get("type"),
                    "member_count": info.get("memberCount"),
                    "api_count": info.get("apiCount"),
                    "created_at": info.get("createdAt"),
                    "updated_at": info.get("updatedAt"),
                }
            }
        return {"data": None, "message": "无法获取 Apifox 项目信息"}
    except Exception as e:
        return {"data": None, "message": f"获取失败: {str(e)}"}


@router.get("/{project_id}/apifox-collections", response_model=dict[str, Any])
async def get_apifox_collections_realtime(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    access_token: str | None = Query(None, description="Apifox Access Token"),
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if not project.apifox_project_id:
        return {"data": [], "message": "项目未关联 Apifox 项目"}
    
    try:
        collections = await apifox_service.get_project_collections(
            project_id=project.apifox_project_id.strip() if project.apifox_project_id else "",
            access_token=access_token,
        )
        
        from app.models.execution import TestExecution
        from sqlmodel import select, func
        
        result = []
        for item in collections:
            apifox_id = str(item.get("id"))
            exec_count = session.exec(
                select(func.count(TestExecution.id)).where(
                    TestExecution.apifox_collection_id == apifox_id
                )
            ).one()
            
            existing = get_collection_by_apifox_id(
                session=session,
                apifox_collection_id=apifox_id,
            )
            
            result.append({
                "id": apifox_id,
                "name": item.get("name"),
                "type": item.get("type"),
                "description": item.get("description"),
                "execution_count": exec_count,
                "is_synced": existing is not None,
                "local_id": str(existing.id) if existing else None,
            })
        
        return {"data": result, "count": len(result)}
    except Exception as e:
        return {"data": [], "message": f"获取失败: {str(e)}"}


@router.get("/{project_id}/executions", response_model=dict[str, Any])
async def get_project_executions(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    from app.models.execution import TestExecution
    from sqlmodel import select, func
    
    total = session.exec(
        select(func.count(TestExecution.id)).where(
            TestExecution.project_id == project_id
        )
    ).one()
    
    executions = session.exec(
        select(TestExecution)
        .where(TestExecution.project_id == project_id)
        .order_by(TestExecution.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    
    result = []
    for e in executions:
        result.append({
            "id": str(e.id),
            "apifox_collection_id": e.apifox_collection_id,
            "collection_name": e.collection_name,
            "collection_type": e.collection_type,
            "status": e.status,
            "total_cases": e.total_cases,
            "passed_cases": e.passed_cases,
            "failed_cases": e.failed_cases,
            "skipped_cases": e.skipped_cases,
            "duration": e.duration,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "error_message": e.error_message,
            "environment": e.environment,
            "has_mongodb_report": e.has_mongodb_report,
        })
    
    return {"data": result, "count": total}


@router.post("/{project_id}/sync", response_model=dict)
async def sync_project_from_apifox(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    access_token: str | None = Query(None, description="Apifox Access Token（可选，默认使用系统配置）"),
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if not project.apifox_project_id:
        raise HTTPException(status_code=400, detail="项目未关联 Apifox 项目")
    
    try:
        collections_data = await apifox_service.get_project_collections(
            project_id=project.apifox_project_id.strip() if project.apifox_project_id else "",
            access_token=access_token,
        )
        
        synced_count = 0
        for item in collections_data:
            existing = get_collection_by_apifox_id(
                session=session,
                apifox_collection_id=str(item.get("id")),
            )
            if not existing:
                collection_in = CollectionCreate(
                    project_id=project.id,
                    name=item.get("name", ""),
                    apifox_collection_id=str(item.get("id")),
                    collection_type=item.get("type", "test-suite"),
                    description=item.get("description"),
                )
                create_collection(session=session, collection_in=collection_in)
                synced_count += 1
        
        from app.models.base import get_datetime_china
        project.last_sync_at = get_datetime_china()
        session.add(project)
        session.commit()
        
        return {
            "message": f"同步完成，新增 {synced_count} 个测试集合",
            "synced_count": synced_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/{project_id}/collections", response_model=CollectionsPublic)
async def list_project_collections(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    is_active: bool | None = Query(None),
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    collections = get_collections_by_project(
        session=session,
        project_id=str(project_id),
        is_active=is_active,
    )
    
    from app.models.execution import TestExecution
    from sqlmodel import select, func
    
    result = []
    for c in collections:
        exec_count = session.exec(
            select(func.count(TestExecution.id)).where(
                TestExecution.apifox_collection_id == c.apifox_collection_id
            )
        ).one()
        
        last_exec = session.exec(
            select(TestExecution)
            .where(TestExecution.apifox_collection_id == c.apifox_collection_id)
            .order_by(TestExecution.created_at.desc())
            .limit(1)
        ).first()
        
        result.append(
            CollectionPublic(
                id=c.id,
                project_id=c.project_id,
                name=c.name,
                apifox_collection_id=c.apifox_collection_id,
                collection_type=c.collection_type,
                description=c.description,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
                execution_count=exec_count,
                last_execution_at=last_exec.created_at if last_exec else None,
            )
        )
    
    return CollectionsPublic(data=result, count=len(result))


@router.post("/{project_id}/collections", response_model=CollectionPublic)
async def create_project_collection(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_id: uuid.UUID,
    collection_in: CollectionCreate,
) -> Any:
    project = get_project(session=session, project_id=str(project_id))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    collection_in.project_id = project_id
    collection = create_collection(session=session, collection_in=collection_in)
    
    return CollectionPublic(
        id=collection.id,
        project_id=collection.project_id,
        name=collection.name,
        apifox_collection_id=collection.apifox_collection_id,
        collection_type=collection.collection_type,
        description=collection.description,
        is_active=collection.is_active,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.put("/collections/{collection_id}", response_model=CollectionPublic)
async def update_collection_detail(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    collection_id: uuid.UUID,
    collection_in: CollectionUpdate,
) -> Any:
    collection = get_collection(session=session, collection_id=str(collection_id))
    if not collection:
        raise HTTPException(status_code=404, detail="测试集合不存在")
    
    collection = update_collection(
        session=session,
        db_collection=collection,
        collection_in=collection_in,
    )
    
    return CollectionPublic(
        id=collection.id,
        project_id=collection.project_id,
        name=collection.name,
        apifox_collection_id=collection.apifox_collection_id,
        collection_type=collection.collection_type,
        description=collection.description,
        is_active=collection.is_active,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.delete("/collections/{collection_id}", response_model=Message)
async def delete_collection_by_id(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    collection_id: uuid.UUID,
) -> Any:
    collection = get_collection(session=session, collection_id=str(collection_id))
    if not collection:
        raise HTTPException(status_code=404, detail="测试集合不存在")
    
    delete_collection(session=session, collection_id=str(collection_id))
    return Message(message="测试集合已删除")
