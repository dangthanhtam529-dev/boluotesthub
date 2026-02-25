import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('PROJECT_NAME', '缺陷管理系统')
os.environ.setdefault('MYSQL_SERVER', 'localhost')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('MYSQL_DB', 'qa_assistant')
os.environ.setdefault('MYSQL_USER', 'root')
os.environ.setdefault('MYSQL_PASSWORD', '123456')
os.environ.setdefault('MONGODB_URL', 'mongodb://localhost:27017')
os.environ.setdefault('MONGODB_DB_NAME', 'test_platform')
os.environ.setdefault('SECRET_KEY', 'changethis')
os.environ.setdefault('APIFOX_ACCESS_TOKEN', 'afxp_8a53312G2fCZen2C4pyPor0MGME8wT9eWe7B')
os.environ.setdefault('APIFOX_PROJECT_ID', '7822130')

from sqlmodel import Session, text
from app.core.db import engine

print("=== 定时任务数据 ===")
with Session(engine) as session:
    result = session.exec(text('SELECT id, name, collection_id, collection_type, environment, is_enabled FROM scheduled_tasks'))
    for row in result:
        data = dict(row._mapping)
        print(f"ID: {data['id']}")
        print(f"名称: {data['name']}")
        print(f"collection_id: {data['collection_id']}")
        print(f"collection_type: {data['collection_type']}")
        print(f"environment: {data['environment']}")
        print(f"is_enabled: {data['is_enabled']}")
        print("---")
