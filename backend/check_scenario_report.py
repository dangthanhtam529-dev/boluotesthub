import json
from pathlib import Path

# 读取报告文件
json_files = list(Path('./test-output').glob('*.json'))
if json_files:
    with open(json_files[0], 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    print("=== 测试场景报告分析 ===\n")
    
    # 检查 collection
    collection = report.get('collection', {})
    print(f"场景名称: {collection.get('name', 'N/A')}")
    
    items = collection.get('item', [])
    print(f"场景中的接口数量: {len(items)}")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.get('name', 'N/A')}")
    
    # 检查执行结果
    result = report.get('result', {})
    stats = result.get('stats', {})
    
    print(f"\n=== 执行统计 ===")
    print(f"requests: {stats.get('requests', {})}")
    print(f"tests: {stats.get('tests', {})}")
    
    # 检查 stepTree
    step_tree = result.get('stepTree', [])
    print(f"\n实际执行步骤数: {len(step_tree)}")
    for step in step_tree:
        print(f"  - {step.get('name', 'N/A')} (type: {step.get('type')}, status: {step.get('status')})")
    
    # 检查失败信息
    failures = result.get('failures', [])
    print(f"\n失败数: {len(failures)}")
    
else:
    print("没有找到报告文件")
