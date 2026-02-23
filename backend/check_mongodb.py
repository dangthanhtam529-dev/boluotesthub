import asyncio
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from app.core.mongodb import init_mongodb, get_mongodb_db

init_mongodb()

async def check():
    try:
        db = get_mongodb_db()
        collection = db['test_reports']
        count = await collection.count_documents({})
        print(f'MongoDB 中报告数量: {count}')

        # 列出最近的报告
        async for doc in collection.find().limit(5):
            print(f"ID: {doc.get('_id')}, execution_id: {doc.get('execution_id')}, created_at: {doc.get('created_at')}")
    except Exception as e:
        print(f"错误: {e}")

asyncio.run(check())
