import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models.item import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate
from app.models import Message
from app.services.audit_log import create_audit_log
from app.models.audit_log import AuditStatus

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Item)
        count = session.exec(count_statement).one()
        statement = (
            select(Item).order_by(col(Item.created_at).desc()).offset(skip).limit(limit)
        )
        items = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Item)
            .where(Item.owner_id == current_user.id)
            .order_by(col(Item.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
        items = session.exec(statement).all()

    return ItemsPublic(data=items, count=count)


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate, request: Request
) -> Any:
    """
    Create new item.
    """
    item = Item.model_validate(item_in, update={"owner_id": current_user.id})
    session.add(item)
    session.commit()
    session.refresh(item)
    create_audit_log(
        session=session,
        action="create",
        resource_type="item",
        resource_id=str(item.id),
        resource_name=item.title,
        status=AuditStatus.SUCCESS,
        request=request,
        actor=current_user,
        after=item,
    )
    return item


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
    request: Request,
) -> Any:
    """
    Update an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    before = item.model_dump()
    update_dict = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    diff_summary = ",".join(sorted(update_dict.keys())) if update_dict else None
    create_audit_log(
        session=session,
        action="update",
        resource_type="item",
        resource_id=str(item.id),
        resource_name=item.title,
        status=AuditStatus.SUCCESS,
        request=request,
        actor=current_user,
        before=before,
        after=item,
        diff_summary=diff_summary,
    )
    return item


@router.delete("/{id}", response_model=Message)
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID, request: Request
) -> Message:
    """
    Delete an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    before = item.model_dump()
    session.delete(item)
    session.commit()
    create_audit_log(
        session=session,
        action="delete",
        resource_type="item",
        resource_id=str(id),
        resource_name=item.title,
        status=AuditStatus.SUCCESS,
        request=request,
        actor=current_user,
        before=before,
    )
    return Message(message="Item deleted successfully")
