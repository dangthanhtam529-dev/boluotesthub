"""
测试完整流程：执行测试 -> 保存到 MongoDB
"""
import asyncio
import json
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from app.services.apifox import apifox_service
from app.services.mongodb_report import MongoDBReportService

async def test_full_flow():
    try:
        print("=== 测试完整流程 ===")
        
        # 1. 执行测试
        print("1. 执行测试套件 8145...")
        report = apifox_service.run_collection(
            collection_id="8145",
            collection_type="test-suite",
        )
        
        print(f"测试执行成功! 报告大小: {len(json.dumps(report))} 字节")
        
        # 2. 直接保存到 MongoDB
        print("\n2. 保存报告到 MongoDB...")
        mongo_id = await MongoDBReportService.save_report(
            execution_id="test_full_flow_123",
            apifox_collection_id="8145",
            project_name="开源商城",
            environment="",
            report_data=report,
        )
        
        print(f"MongoDB 保存成功! ID: {mongo_id}")
        
        # 3. 验证保存结果
        print("\n3. 验证保存结果...")
        from app.core.mongodb import get_mongodb_db
        db = get_mongodb_db()
        collection = db['test_reports']
        
        count = await collection.count_documents({})
        print(f"集合中文档数量: {count}")
        
        # 查看刚保存的文档
        doc = await collection.find_one({"execution_id": "test_full_flow_123"})
        if doc:
            print(f"找到刚保存的文档! ID: {doc.get('_id')}")
            print(f"报告大小: {doc.get('size_bytes')} 字节")
        else:
            print("未找到刚保存的文档")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_flow())
