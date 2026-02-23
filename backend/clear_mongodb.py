import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_platform']
    
    # 删除所有报告数据
    result = await db.test_reports.delete_many({})
    print(f"Deleted {result.deleted_count} test reports from MongoDB")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(clear())
