import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

async def test_apifox_params():
    token = "afxp_5e19a7v30vQ1ijQUC2XT3FIyMNe5xLqM65Ne"
    project_id = "7822130"
    scenario_id = "7936775"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cmd = f'npx apifox run -t {scenario_id} --access-token {token} --project {project_id} -r json --out-dir {temp_dir} --verbose'
        
        print(f"Command: {cmd}")
        print("=" * 50)
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120,
        )
        
        print(f"Return code: {result.returncode}")
        print(f"\nStdout:\n{result.stdout[:2000]}")
        print(f"\nStderr:\n{result.stderr[:1000]}")
        
        import glob
        json_files = glob.glob(str(Path(temp_dir) / "**" / "*.json"), recursive=True)
        print(f"\nJSON files found: {json_files}")
        
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            with open('test_report_verbose.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"\nReport saved to test_report_verbose.json")
            
            result_data = report.get('result', {})
            print(f"\nResult keys: {list(result_data.keys())}")
            
            if 'executions' in result_data:
                print(f"Executions count: {len(result_data['executions'])}")
            else:
                print("No 'executions' in result")
            
            run_data = report.get('run', {})
            print(f"\nRun keys: {list(run_data.keys())}")
            
            if 'executions' in run_data:
                print(f"Run executions count: {len(run_data['executions'])}")
                for i, ex in enumerate(run_data['executions'][:3]):
                    print(f"  Execution {i}: {ex.get('item', {}).get('name', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(test_apifox_params())
