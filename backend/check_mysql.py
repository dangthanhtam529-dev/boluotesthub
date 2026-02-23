import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from sqlmodel import Session, select
from app.core.db import engine
from app.models.execution import TestExecution

with Session(engine) as session:
    executions = session.exec(select(TestExecution).order_by(TestExecution.created_at.desc()).limit(5)).all()
    print(f"MySQL 中最近的执行记录数量: {len(executions)}")
    for e in executions:
        print(f"ID: {e.id}, 状态: {e.status}, 用例数: {e.total_cases}, MongoDB报告: {e.has_mongodb_report}, report_json: {'有' if e.report_json else '无'}")
