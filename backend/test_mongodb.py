import asyncio
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from datetime import datetime
from app.core.mongodb import init_mongodb, get_mongodb_db
from app.services.mongodb_report import MongoDBReportService

init_mongodb()

async def test_mongodb_save():
    try:
        # 测试 MongoDB 连接
        db = get_mongodb_db()
        print(f"MongoDB 数据库: {db.name}")
        
        # 测试集合
        collection = db['test_reports']
        print(f"集合: {collection.name}")
        
        # 测试插入文档
        test_document = {
            "execution_id": "test_123",
            "apifox_collection_id": "8145",
            "project_name": "测试项目",
            "environment": "",
            "report": {"result": {"stats": {"tests": {"total": 1}}}},
            "metrics": {},
            "failed_cases": [],
            "created_at": datetime.utcnow(),
            "size_bytes": 100,
        }
        
        print("尝试插入测试文档...")
        result = await collection.insert_one(test_document)
        print(f"插入成功! 文档ID: {result.inserted_id}")
        
        # 测试查询
        count = await collection.count_documents({})
        print(f"集合中文档数量: {count}")
        
        # 测试 MongoDBReportService.save_report
        print("\n测试 MongoDBReportService.save_report...")
        test_report_data = {
            "result": {
                "stats": {
                    "tests": {
                        "total": 1,
                        "failed": 0,
                        "pending": 0
                    }
                },
                "timings": {
                    "started": 1739265600000,
                    "completed": 1739265601000,
                    "responseAverage": 100,
                    "responseMax": 200,
                    "responseMin": 50
                },
                "failures": []
            }
        }
        
        mongo_id = await MongoDBReportService.save_report(
            execution_id="test_456",
            apifox_collection_id="8145",
            project_name="测试项目",
            environment="",
            report_data=test_report_data,
        )
        print(f"save_report 成功! MongoDB ID: {mongo_id}")
        
        # 再次查询
        count_after = await collection.count_documents({})
        print(f"保存后文档数量: {count_after}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mongodb_save())
