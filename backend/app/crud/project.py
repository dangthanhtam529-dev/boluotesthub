from sqlmodel import Session, select, func
import uuid
from app.models.base import get_datetime_china
from app.models.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    Collection,
    CollectionCreate,
    CollectionUpdate,
    ProjectStats,
)
from app.models.execution import TestExecution


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)


def create_project(*, session: Session, project_in: ProjectCreate, owner_id: str) -> Project:
    db_obj = Project.model_validate(project_in, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_project(*, session: Session, project_id: str) -> Project | None:
    return session.get(Project, _to_uuid(project_id))


def get_projects(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 20,
    owner_id: str | None = None,
    is_active: bool | None = None,
) -> list[Project]:
    statement = select(Project)
    if owner_id:
        statement = statement.where(Project.owner_id == owner_id)
    if is_active is not None:
        statement = statement.where(Project.is_active == is_active)
    statement = statement.order_by(Project.created_at.desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_projects(
    *,
    session: Session,
    owner_id: str | None = None,
    is_active: bool | None = None,
) -> int:
    statement = select(func.count(Project.id))
    if owner_id:
        statement = statement.where(Project.owner_id == owner_id)
    if is_active is not None:
        statement = statement.where(Project.is_active == is_active)
    return session.exec(statement).one()


def update_project(
    *,
    session: Session,
    db_project: Project,
    project_in: ProjectUpdate,
) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)
    db_project.sqlmodel_update(update_data)
    db_project.updated_at = get_datetime_china()
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


def delete_project(*, session: Session, project_id: str) -> bool:
    project = session.get(Project, _to_uuid(project_id))
    if not project:
        return False
    session.delete(project)
    session.commit()
    return True


def get_project_stats(*, session: Session, project_id: str) -> ProjectStats:
    pid = _to_uuid(project_id)
    collection_count = session.exec(
        select(func.count(Collection.id)).where(Collection.project_id == pid)
    ).one()
    
    execution_count = session.exec(
        select(func.count(TestExecution.id)).where(TestExecution.project_id == pid)
    ).one()
    
    executions = session.exec(
        select(TestExecution)
        .where(TestExecution.project_id == pid)
        .order_by(TestExecution.created_at.desc())
        .limit(10)
    ).all()
    
    total_passed = sum(e.passed_cases or 0 for e in executions)
    total_failed = sum(e.failed_cases or 0 for e in executions)
    total = total_passed + total_failed
    pass_rate = (total_passed / total * 100) if total > 0 else 0
    
    recent = [
        {
            "id": str(e.id),
            "status": e.status,
            "total_cases": e.total_cases,
            "passed_cases": e.passed_cases,
            "failed_cases": e.failed_cases,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in executions[:5]
    ]
    
    return ProjectStats(
        total_collections=collection_count,
        total_executions=execution_count,
        total_passed=total_passed,
        total_failed=total_failed,
        pass_rate=round(pass_rate, 2),
        recent_executions=recent,
    )


def create_collection(*, session: Session, collection_in: CollectionCreate) -> Collection:
    db_obj = Collection.model_validate(collection_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_collection(*, session: Session, collection_id: str) -> Collection | None:
    return session.get(Collection, _to_uuid(collection_id))


def get_collections_by_project(
    *,
    session: Session,
    project_id: str,
    is_active: bool | None = None,
) -> list[Collection]:
    pid = _to_uuid(project_id)
    statement = select(Collection).where(Collection.project_id == pid)
    if is_active is not None:
        statement = statement.where(Collection.is_active == is_active)
    statement = statement.order_by(Collection.created_at.desc())
    return list(session.exec(statement).all())


def update_collection(
    *,
    session: Session,
    db_collection: Collection,
    collection_in: CollectionUpdate,
) -> Collection:
    update_data = collection_in.model_dump(exclude_unset=True)
    db_collection.sqlmodel_update(update_data)
    db_collection.updated_at = get_datetime_china()
    session.add(db_collection)
    session.commit()
    session.refresh(db_collection)
    return db_collection


def delete_collection(*, session: Session, collection_id: str) -> bool:
    collection = session.get(Collection, _to_uuid(collection_id))
    if not collection:
        return False
    session.delete(collection)
    session.commit()
    return True


def get_collection_by_apifox_id(
    *,
    session: Session,
    apifox_collection_id: str,
) -> Collection | None:
    statement = select(Collection).where(Collection.apifox_collection_id == apifox_collection_id)
    return session.exec(statement).first()
