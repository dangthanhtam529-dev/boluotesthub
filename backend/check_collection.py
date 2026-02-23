import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_platform']
    
    # 查看最新报告的 collection 结构
    doc = await db.test_reports.find_one(sort=[('created_at', -1)])
    if doc:
        report = doc.get('report', {})
        collection = report.get('collection', {})
        
        print(f"Collection name: {collection.get('name')}")
        print(f"Collection ID: {collection.get('id')}")
        print()
        
        items = collection.get('item', [])
        print(f"Total items in collection: {len(items)}")
        print()
        
        for i, item in enumerate(items, 1):
            print(f"Item {i}:")
            print(f"  Name: {item.get('name')}")
            print(f"  Type: {item.get('type', 'N/A')}")
            print(f"  ID: {item.get('id', 'N/A')}")
            
            # 检查 request
            request = item.get('request', {})
            if request:
                print(f"  Request method: {request.get('method', 'N/A')}")
                url = request.get('url', {})
                if isinstance(url, dict):
                    print(f"  Request URL: {url.get('raw', 'N/A')}")
                else:
                    print(f"  Request URL: {url}")
            
            # 检查子 items
            sub_items = item.get('item', [])
            if sub_items:
                print(f"  Sub-items count: {len(sub_items)}")
                for j, sub in enumerate(sub_items, 1):
                    print(f"    {j}. {sub.get('name')} ({sub.get('type', 'N/A')})")
            print()
        
        # 也检查 result 中的 executions
        result = report.get('result', {})
        step_tree = result.get('stepTree', [])
        print(f"StepTree items: {len(step_tree)}")
        for step in step_tree:
            print(f"  - Ref: {step.get('ref')}, Type: {step.get('type')}")
            
    else:
        print('No reports found')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
