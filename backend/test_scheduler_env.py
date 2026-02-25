"""
定时任务环境诊断脚本

用途：在定时任务中运行此脚本，检查环境变量和配置是否正确

使用方法：
1. 在 Windows 任务计划程序中创建一个新任务
2. 操作：python.exe G:\agent_eaplore\full-stack-fastapi-template-master\backend\test_scheduler_env.py
3. 起始于：G:\agent_eaplore\full-stack-fastapi-template-master
4. 运行后查看 backend/test_scheduler_env_output.log
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 获取项目根目录
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(current_file)
project_root = os.path.dirname(backend_dir)

# 输出文件
output_file = os.path.join(backend_dir, "test_scheduler_env_output.log")

def log(message: str):
    """写入日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# 清空旧日志
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"=== 定时任务环境诊断开始 ===\n")
    f.write(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

log("=" * 50)
log("1. 基础环境信息")
log("=" * 50)
log(f"Python 版本：{sys.version}")
log(f"当前工作目录：{os.getcwd()}")
log(f"脚本文件路径：{current_file}")
log(f"项目根目录：{project_root}")
log(f"当前用户：{os.environ.get('USERNAME', 'N/A')}")
log(f"计算机名：{os.environ.get('COMPUTERNAME', 'N/A')}")

log("\n" + "=" * 50)
log("2. 环境变量检查")
log("=" * 50)
log(f"APIFOX_ACCESS_TOKEN 是否存在：{'APIFOX_ACCESS_TOKEN' in os.environ}")
if 'APIFOX_ACCESS_TOKEN' in os.environ:
    token = os.environ.get('APIFOX_ACCESS_TOKEN', '')
    log(f"APIFOX_ACCESS_TOKEN 长度：{len(token)}")
    log(f"APIFOX_ACCESS_TOKEN 前缀：{token[:15]}..." if len(token) > 15 else f"APIFOX_ACCESS_TOKEN: {token}")

log(f"APIFOX_PROJECT_ID 是否存在：{'APIFOX_PROJECT_ID' in os.environ}")
if 'APIFOX_PROJECT_ID' in os.environ:
    log(f"APIFOX_PROJECT_ID: {os.environ.get('APIFOX_PROJECT_ID', 'N/A')}")

log(f"PATH 长度：{len(os.environ.get('PATH', ''))}")
log(f"PATH 前缀：{os.environ.get('PATH', '')[:200]}...")

log("\n" + "=" * 50)
log("3. 检查 Node.js 和 npm")
log("=" * 50)

# 检查 node
import subprocess
try:
    result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
    log(f"Node.js 版本：{result.stdout.strip() if result.returncode == 0 else '未找到'}")
    if result.returncode != 0:
        log(f"Node.js 错误：{result.stderr.strip()}")
except FileNotFoundError:
    log("Node.js: 未找到 (不在 PATH 中)")
except Exception as e:
    log(f"Node.js 检查异常：{e}")

# 检查 npm
try:
    result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10)
    log(f"npm 版本：{result.stdout.strip() if result.returncode == 0 else '未找到'}")
    if result.returncode != 0:
        log(f"npm 错误：{result.stderr.strip()}")
except FileNotFoundError:
    log("npm: 未找到 (不在 PATH 中)")
except Exception as e:
    log(f"npm 检查异常：{e}")

# 检查 npx
try:
    result = subprocess.run(["npx", "--version"], capture_output=True, text=True, timeout=10)
    log(f"npx 版本：{result.stdout.strip() if result.returncode == 0 else '未找到'}")
    if result.returncode != 0:
        log(f"npx 错误：{result.stderr.strip()}")
except FileNotFoundError:
    log("npx: 未找到 (不在 PATH 中)")
except Exception as e:
    log(f"npx 检查异常：{e}")

# 检查常见的 Node.js 安装路径
log("\n检查常见安装路径:")
node_paths = [
    r"C:\Program Files\nodejs",
    r"C:\Program Files (x86)\nodejs",
    os.path.join(os.environ.get('APPDATA', ''), 'npm'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
]
for path in node_paths:
    if os.path.exists(path):
        log(f"  ✓ {path}")
        # 列出目录内容
        try:
            files = os.listdir(path)
            node_exec = [f for f in files if 'node' in f.lower()]
            npm_exec = [f for f in files if 'npm' in f.lower()]
            if node_exec:
                log(f"    Node 相关文件：{node_exec[:5]}")
            if npm_exec:
                log(f"    NPM 相关文件：{npm_exec[:5]}")
        except Exception as e:
            log(f"    无法列出目录：{e}")
    else:
        log(f"  ✗ {path} (不存在)")

log("\n" + "=" * 50)
log("4. 测试 Apifox CLI")
log("=" * 50)

# 测试 apifox CLI 是否可用
try:
    result = subprocess.run(
        ["npx", "apifox", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        env=os.environ.copy()
    )
    if result.returncode == 0:
        log(f"Apifox CLI 版本：{result.stdout.strip()}")
    else:
        log(f"Apifox CLI 检查失败:")
        log(f"  stdout: {result.stdout[:500] if result.stdout else 'None'}")
        log(f"  stderr: {result.stderr[:500] if result.stderr else 'None'}")
except FileNotFoundError:
    log("Apifox CLI (npx): 未找到")
except subprocess.TimeoutExpired:
    log("Apifox CLI 检查超时")
except Exception as e:
    log(f"Apifox CLI 检查异常：{e}")

log("\n" + "=" * 50)
log("5. .env 文件检查")
log("=" * 50)

env_file = os.path.join(project_root, ".env")
log(f".env 文件路径：{env_file}")
if os.path.exists(env_file):
    log(f".env 文件大小：{os.path.getsize(env_file)} 字节")
    
    # 检查关键配置
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
        log(".env 文件加载成功")
        
        # 重新检查环境变量
        log(f"\n加载后 - APIFOX_ACCESS_TOKEN 是否存在：{'APIFOX_ACCESS_TOKEN' in os.environ}")
        log(f"加载后 - APIFOX_PROJECT_ID: {os.environ.get('APIFOX_PROJECT_ID', 'N/A')}")
    except Exception as e:
        log(f".env 文件加载失败：{e}")
else:
    log(".env 文件不存在!")

log("\n" + "=" * 50)
log("6. 网络连通性测试")
log("=" * 50)

import socket
try:
    socket.setdefaulttimeout(5)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('api.apifox.com', 443))
    sock.close()
    if result == 0:
        log("✓ 可以连接到 api.apifox.com:443")
    else:
        log(f"✗ 无法连接到 api.apifox.com:443 (错误码：{result})")
except Exception as e:
    log(f"✗ 网络测试异常：{e}")

log("\n" + "=" * 50)
log("诊断完成")
log("=" * 50)
log(f"\n日志文件已保存到：{output_file}")
log("请将此文件内容发送给开发者以排查问题。")
