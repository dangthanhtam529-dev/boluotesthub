"""
定时任务修复验证脚本

使用方法：
    python test_scheduler_fix.py

此脚本会：
1. 检查 .env 文件是否能正确读取
2. 检查 APIFOX_ACCESS_TOKEN 和 PROJECT_ID
3. 模拟定时任务环境执行 CLI 命令
4. 输出详细的诊断信息
"""

import os
import sys
import subprocess
from pathlib import Path

# 获取项目根目录
CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

print("=" * 80)
print("定时任务修复验证脚本")
print("=" * 80)

# 1. 检查 .env 文件
env_file = os.path.join(PROJECT_ROOT, ".env")
print(f"\n【1】检查 .env 文件")
print(f"    项目根目录：{PROJECT_ROOT}")
print(f"    .env 文件路径：{env_file}")
print(f"    .env 文件存在：{os.path.exists(env_file)}")

if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        has_token = 'APIFOX_ACCESS_TOKEN' in content
        has_project = 'APIFOX_PROJECT_ID' in content
        print(f"    包含 APIFOX_ACCESS_TOKEN: {has_token}")
        print(f"    包含 APIFOX_PROJECT_ID: {has_project}")
        
        # 提取 token 前缀
        for line in content.split('\n'):
            if line.startswith('APIFOX_ACCESS_TOKEN='):
                token_value = line.split('=', 1)[1].strip()
                print(f"    APIFOX_ACCESS_TOKEN 前缀：{token_value[:15]}..." if token_value else "    APIFOX_ACCESS_TOKEN: 空")
            elif line.startswith('APIFOX_PROJECT_ID='):
                project_value = line.split('=', 1)[1].strip()
                print(f"    APIFOX_PROJECT_ID: {project_value}")

# 2. 加载 .env 并检查环境变量
from dotenv import load_dotenv
print(f"\n【2】加载 .env 文件")
load_dotenv(env_file, override=True, verbose=True)

token = os.environ.get('APIFOX_ACCESS_TOKEN')
project_id = os.environ.get('APIFOX_PROJECT_ID')
print(f"    加载后 APIFOX_ACCESS_TOKEN 是否存在：{bool(token)}")
print(f"    加载后 APIFOX_PROJECT_ID: {project_id}")

# 3. 模拟定时任务环境
print(f"\n【3】模拟定时任务环境")
os.chdir(PROJECT_ROOT)
print(f"    切换工作目录到：{os.getcwd()}")

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

npm_global_path = os.path.join(os.environ.get('APPDATA', ''), 'npm')
node_path = r"C:\Program Files\nodejs"
current_path = os.environ.get('PATH', '')
new_paths = [p for p in [node_path, npm_global_path] if os.path.exists(p) and p not in current_path]
if new_paths:
    os.environ['PATH'] = os.pathsep.join(new_paths + [current_path])
    print(f"    已添加 PATH: {new_paths}")
print(f"    更新后 PATH 前缀：{os.environ.get('PATH', '')[:200]}...")

# 4. 测试 CLI 命令
print(f"\n【4】测试 Apifox CLI 命令")
if token and project_id:
    test_cmd = f"npx apifox run --test-suite 8145 --access-token {token} --project {project_id} -r json --verbose"
    print(f"    测试命令：{test_cmd[:100]}...")
    
    exec_env = os.environ.copy()
    
    print(f"    执行 CLI 命令...")
    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
            env=exec_env,
        )
        
        print(f"    返回码：{result.returncode}")
        
        if result.returncode == 0:
            print(f"    OK CLI 执行成功！")
            if result.stdout:
                # 尝试解析 JSON
                import json
                try:
                    report = json.loads(result.stdout)
                    stats = report.get('result', {}).get('stats', {})
                    steps = stats.get('steps', {})
                    print(f"    测试用例数：{steps.get('total', 0)}")
                    print(f"    通过：{steps.get('passed', 0)}")
                    print(f"    失败：{steps.get('failed', 0)}")
                except:
                    print(f"    stdout 前 200 字符：{result.stdout[:200]}")
        else:
                print(f"    FAIL CLI 执行失败")
            print(f"    stderr: {result.stderr[:500]}")
            print(f"    stdout: {result.stdout[:500]}")
            
        print(f"    FAIL CLI 执行超时")
    except subprocess.TimeoutExpired:
        print(f"    FAIL CLI 执行超时")
    except Exception as e:
        print(f"    FAIL 异常：{e}")
else:
    print(f"    缺少 token 或 project_id，跳过 CLI 测试")

# 5. 总结
print(f"\n【5】诊断总结")
print(f"    .env 文件存在：{os.path.exists(env_file)}")
print(f"    APIFOX_ACCESS_TOKEN 可用：{bool(token)}")
print(f"    APIFOX_PROJECT_ID 可用：{bool(project_id)}")
print(f"    工作目录正确：{os.getcwd() == PROJECT_ROOT}")
print(f"    PATH 包含 nodejs：{'nodejs' in os.environ.get('PATH', '').lower()}")

if token and project_id:
    print(f"\n✓ 所有检查通过！定时任务应该能正常工作。")
    print(f"  如果仍有问题，请查看后端日志中的详细错误信息。")
else:
    print(f"\n✗ 检查失败！请确保 .env 文件配置正确。")

print("\n" + "=" * 80)
