"""
测试报告数据结构，检查是否能正确保存到 MongoDB
"""
import asyncio
import json
import sys
sys.path.insert(0, 'G:\\agent_eaplore\\full-stack-fastapi-template-master\\backend')

from app.services.apifox import apifox_service

async def test_report_structure():
    try:
        print("=== 测试报告数据结构 ===")
        
        # 执行测试
        print("执行测试套件 8145...")
        report = apifox_service.run_collection(
            collection_id="8145",
            collection_type="test-suite",
        )
        
        print(f"测试执行成功!")
        print(f"报告类型: {type(report)}")
        print(f"报告数据大小: {len(json.dumps(report))} 字节")
        
        # 检查报告结构
        print("\n报告结构:")
        print(f"- 顶层键: {list(report.keys())}")
        
        if "result" in report:
            result = report["result"]
            print(f"- result 键: {list(result.keys())}")
            
            if "stats" in result:
                stats = result["stats"]
                print(f"- stats: {stats}")
            
            if "timings" in result:
                timings = result["timings"]
                print(f"- timings 键: {list(timings.keys())}")
            
            if "failures" in result:
                failures = result["failures"]
                print(f"- failures 数量: {len(failures)}")
        
        # 测试 JSON 序列化
        print("\n测试 JSON 序列化...")
        try:
            json_str = json.dumps(report, ensure_ascii=False)
            print(f"JSON 序列化成功! 长度: {len(json_str)}")
        except Exception as e:
            print(f"JSON 序列化失败: {e}")
            
        # 测试直接插入到 MongoDB
        print("\n测试直接插入到 MongoDB...")
        from app.core.mongodb import get_mongodb_db
        db = get_mongodb_db()
        collection = db['test_reports']
        
        test_doc = {
            "execution_id": "test_structure_123",
            "apifox_collection_id": "8145",
            "project_name": "开源商城",
            "environment": "",
            "report": report,
            "metrics": {},
            "failed_cases": [],
            "size_bytes": len(json.dumps(report)),
        }
        
        try:
            result = await collection.insert_one(test_doc)
            print(f"直接插入成功! ID: {result.inserted_id}")
        except Exception as e:
            print(f"直接插入失败: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_report_structure())
