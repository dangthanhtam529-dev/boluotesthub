import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_platform']
    
    # 查看最新报告的原始结构
    doc = await db.test_reports.find_one(sort=[('created_at', -1)])
    if doc:
        report = doc.get('report', {})
        
        # 保存完整报告到文件以便查看
        with open('last_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("完整报告已保存到 last_report.json")
        
        # 检查 collection 信息
        collection = report.get('collection', {})
        print(f"\ncollection name: {collection.get('name')}")
        print(f"collection id: {collection.get('id')}")
        
        # 检查 item 列表
        items = collection.get('item', [])
        print(f"\ncollection items 数量: {len(items)}")
        
        for i, item in enumerate(items, 1):
            print(f"  Item {i}: {item.get('name')} (type: {item.get('type')})")
            
        # 检查 result 中的 executions
        result = report.get('result', {})
        step_tree = result.get('stepTree', {})
        print(f"\nstepTree keys: {list(step_tree.keys())}")
        
        children = step_tree.get('children', [])
        print(f"stepTree children 数量: {len(children)}")
        
        for i, child in enumerate(children, 1):
            print(f"  Child {i}: {child.get('name')} (type: {child.get('type')}, status: {child.get('status')})")
            
    else:
        print('没有找到报告')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
