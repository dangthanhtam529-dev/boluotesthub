from sqlmodel import Session, text
from app.core.db import engine

print("=== 定时任务数据 ===")
with Session(engine) as session:
    result = session.exec(text('SELECT id, name, collection_id, collection_type, environment, is_enabled FROM scheduled_tasks'))
    rows = result.all()
    print(f"找到 {len(rows)} 条定时任务")
    for row in rows:
        print(f"ID: {row.id}, 名称: {row.name}, collection_id: {row.collection_id}, collection_type: {row.collection_type}, environment: {row.environment}, is_enabled: {row.is_enabled}")
