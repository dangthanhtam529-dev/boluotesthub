# 项目相关 CRUD 操作
import uuid
from sqlmodel import Session, select
from app.models.item import Item, ItemCreate


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    """创建新项目"""
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def get_item_by_id(*, session: Session, item_id: uuid.UUID) -> Item | None:
    """通过 ID 获取项目"""
    statement = select(Item).where(Item.id == item_id)
    return session.exec(statement).first()


def get_items_by_owner(*, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Item]:
    """获取用户的所有项目"""
    statement = select(Item).where(Item.owner_id == owner_id).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def delete_item(*, session: Session, db_item: Item) -> None:
    """删除项目"""
    session.delete(db_item)
    session.commit()