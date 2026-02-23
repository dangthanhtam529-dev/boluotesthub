import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_platform']
    
    # 查看所有报告
    cursor = db.test_reports.find().sort('created_at', -1)
    docs = await cursor.to_list(length=10)
    
    print(f"总共有 {len(docs)} 条报告记录\n")
    
    for i, doc in enumerate(docs, 1):
        print(f"=== 报告 {i} ===")
        print(f"  MongoDB ID: {doc['_id']}")
        print(f"  execution_id: {doc.get('execution_id')}")
        print(f"  apifox_collection_id: {doc.get('apifox_collection_id')}")
        print(f"  project_name: {doc.get('project_name')}")
        print(f"  created_at: {doc.get('created_at')}")
        
        # 查看 stats
        report = doc.get('report', {})
        result = report.get('result', {})
        stats = result.get('stats', {})
        
        requests = stats.get('requests', {})
        tests = stats.get('tests', {})
        
        print(f"  requests: {requests.get('total', 0)} total, {requests.get('passed', 0)} passed")
        print(f"  tests: {tests.get('total', 0)} total, {tests.get('passed', 0)} passed")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
