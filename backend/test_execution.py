"""
测试执行脚本 - 使用正确的测试套件 ID 执行测试
"""
import asyncio
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from datetime import datetime
from sqlmodel import Session
from app.core.db import engine
from app.models.execution import TestExecution, ExecutionStatus
from app.services.apifox import apifox_service

async def run_test():
    with Session(engine) as session:
        # 创建执行记录
        execution = TestExecution(
            project_name="开源商城",
            apifox_collection_id="8145",  # 正确的测试套件 ID
            collection_type="test-suite",
            environment=None,
            status=ExecutionStatus.PENDING,
            created_at=datetime.now(),
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)

        print(f"创建执行记录: {execution.id}")

        try:
            # 执行测试
            result = await apifox_service.execute_and_save(
                session=session,
                execution=execution,
                collection_id="8145",
                environment_id=None,
                collection_type="test-suite",
            )

            print(f"执行完成!")
            print(f"状态: {result.status}")
            print(f"总用例数: {result.total_cases}")
            print(f"通过: {result.passed_cases}")
            print(f"失败: {result.failed_cases}")
            print(f"MongoDB报告ID: {result.mongo_report_id}")
            print(f"是否有MongoDB报告: {result.has_mongodb_report}")

        except Exception as e:
            print(f"执行失败: {e}")
            session.refresh(execution)
            print(f"错误信息: {execution.error_message}")

if __name__ == "__main__":
    asyncio.run(run_test())
