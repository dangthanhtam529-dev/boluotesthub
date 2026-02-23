"""
测试 MongoDB 基本连接和操作
"""
import asyncio
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from datetime import datetime
from app.core.mongodb import init_mongodb, get_mongodb_db

async def test_mongodb_basic():
    try:
        print("=== 测试 MongoDB 基本操作 ===")
        
        # 初始化 MongoDB
        init_mongodb()
        
        # 获取数据库
        db = get_mongodb_db()
        print(f"数据库: {db.name}")
        
        # 测试集合
        collection = db['test_reports']
        print(f"集合: {collection.name}")
        
        # 测试插入
        print("\n测试插入文档...")
        test_doc = {
            "execution_id": f"test_basic_{datetime.now().timestamp()}",
            "apifox_collection_id": "8145",
            "project_name": "测试项目",
            "created_at": datetime.utcnow(),
            "test_field": "test_value",
        }
        
        result = await collection.insert_one(test_doc)
        print(f"插入成功! ID: {result.inserted_id}")
        
        # 测试查询
        print("\n测试查询文档...")
        count = await collection.count_documents({})
        print(f"总文档数: {count}")
        
        # 测试查找
        doc = await collection.find_one({"execution_id": test_doc["execution_id"]})
        if doc:
            print(f"找到文档: {doc.get('_id')}")
            print(f"execution_id: {doc.get('execution_id')}")
        else:
            print("未找到文档")
        
        # 测试删除
        print("\n测试删除文档...")
        delete_result = await collection.delete_one({"execution_id": test_doc["execution_id"]})
        print(f"删除结果: {delete_result.deleted_count} 个文档")
        
        # 验证删除
        count_after = await collection.count_documents({})
        print(f"删除后总文档数: {count_after}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mongodb_basic())
