import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_platform']
    
    # 查看最新报告的详细内容
    doc = await db.test_reports.find_one(sort=[('created_at', -1)])
    if doc:
        print('=== 报告基本信息 ===')
        print(f"ID: {doc['_id']}")
        print(f"execution_id: {doc.get('execution_id')}")
        print(f"project_name: {doc.get('project_name')}")
        print(f"apifox_collection_id: {doc.get('apifox_collection_id')}")
        print(f"environment: {doc.get('environment')}")
        print(f"created_at: {doc.get('created_at')}")
        print(f"size_bytes: {doc.get('size_bytes')}")
        
        print('\n=== 性能指标 ===')
        print(json.dumps(doc.get('metrics', {}), indent=2, ensure_ascii=False))
        
        print('\n=== 失败用例 ===')
        failed_cases = doc.get('failed_cases', [])
        print(f"失败用例数: {len(failed_cases)}")
        for case in failed_cases:
            print(f"  - {case.get('name')}: {case.get('error')}")
        
        # 查看完整报告结构
        report = doc.get('report', {})
        result = report.get('result', {})
        
        print('\n=== 完整报告结构 ===')
        print(f"report keys: {list(report.keys())}")
        print(f"result keys: {list(result.keys())}")
        
        # 查看 run 信息
        run = result.get('run', {})
        print(f"\nrun keys: {list(run.keys())}")
        
        # 查看 executions
        executions = run.get('executions', [])
        print(f"\nexecutions 数量: {len(executions)}")
        
        for i, exec_item in enumerate(executions, 1):
            print(f"\n--- Execution {i} ---")
            print(f"  name: {exec_item.get('name')}")
            print(f"  type: {exec_item.get('type')}")
            print(f"  status: {exec_item.get('status')}")
            
            # 查看 item 信息
            item = exec_item.get('item', {})
            if item:
                request = item.get('request', {})
                print(f"  request method: {request.get('method')}")
                print(f"  request url: {request.get('url', {}).get('raw', '')}")
        
        # 查看 stats 详细信息
        print('\n=== Stats 详细 ===')
        stats = result.get('stats', {})
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    else:
        print('没有找到报告')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
