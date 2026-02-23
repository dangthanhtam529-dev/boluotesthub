"""
简单测试脚本 - 执行测试并打印完整输出
"""
import asyncio
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from sqlmodel import Session
from app.core.db import engine
from app.models.execution import TestExecution, ExecutionStatus
from app.services.apifox import apifox_service

async def main():
    print("=== 简单测试 ===")
    
    with Session(engine) as session:
        # 创建执行记录
        execution = TestExecution(
            project_name="开源商城",
            apifox_collection_id="8145",
            collection_type="test-suite",
            environment=None,
            status=ExecutionStatus.PENDING,
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)

        print(f"执行ID: {execution.id}")

        # 执行测试
        print("开始执行测试...")
        result = await apifox_service.execute_and_save(
            session=session,
            execution=execution,
            collection_id="8145",
            collection_type="test-suite",
        )

        print("\n=== 执行结果 ===")
        print(f"状态: {result.status}")
        print(f"总用例数: {result.total_cases}")
        print(f"通过: {result.passed_cases}")
        print(f"失败: {result.failed_cases}")
        print(f"MongoDB报告ID: {result.mongo_report_id}")
        print(f"是否有MongoDB报告: {result.has_mongodb_report}")
        print(f"报告大小: {len(result.report_json) if result.report_json else 0} 字节")

if __name__ == "__main__":
    asyncio.run(main())
