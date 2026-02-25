#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Apifox CLI 调试脚本 - 专门用于诊断定时任务环境问题

使用方法：
    python debug_apifox_cli.py

此脚本会：
1. 检查环境变量（特别是 PATH）
2. 检查 npx/npm 是否可用
3. 执行 Apifox CLI 命令并捕获原始输出
4. 尝试多种编码解码，输出真实错误信息
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

# ============================================================================
# 配置
# ============================================================================

# 获取项目根目录
CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.dirname(CURRENT_FILE)
APP_DIR = os.path.dirname(BACKEND_DIR)
PROJECT_ROOT = os.path.dirname(APP_DIR)
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")

# Apifox 配置
APIFOX_ACCESS_TOKEN = os.environ.get("APIFOX_ACCESS_TOKEN")
APIFOX_PROJECT_ID = os.environ.get("APIFOX_PROJECT_ID")
TEST_SUITE_ID = "8145"  # 从日志中看到的测试套件 ID

print("=" * 80)
print("Apifox CLI 调试脚本 - 诊断定时任务环境问题")
print("=" * 80)

# ============================================================================
# 步骤 1: 检查 .env 文件加载
# ============================================================================

print(f"\n【步骤 1】检查 .env 文件加载")
print(f"项目根目录：{PROJECT_ROOT}")
print(f".env 文件路径：{ENV_FILE_PATH}")
print(f".env 文件存在：{os.path.exists(ENV_FILE_PATH)}")

if os.path.exists(ENV_FILE_PATH):
    print("重新加载 .env 文件...")
    load_dotenv(ENV_FILE_PATH, override=True, verbose=True)
    
    # 检查加载后的环境变量
    token = os.environ.get("APIFOX_ACCESS_TOKEN")
    project_id = os.environ.get("APIFOX_PROJECT_ID")
    
    print(f"APIFOX_ACCESS_TOKEN 是否存在：{bool(token)}")
    print(f"APIFOX_ACCESS_TOKEN 前 15 位：{token[:15]}..." if token else "N/A")
    print(f"APIFOX_PROJECT_ID: {project_id}")
else:
    print("⚠️ .env 文件不存在！")
    sys.exit(1)

# ============================================================================
# 步骤 2: 检查当前工作环境
# ============================================================================

print(f"\n【步骤 2】检查当前工作环境")
print(f"当前工作目录：{os.getcwd()}")
print(f"当前用户：{os.getlogin() if hasattr(os, 'getlogin') else 'N/A'}")
print(f"Python 版本：{sys.version}")
print(f"Python 可执行文件：{sys.executable}")

# 检查环境变量
print(f"\n【环境变量检查】")
print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', '未设置')}")
print(f"PYTHONUTF8: {os.environ.get('PYTHONUTF8', '未设置')}")
print(f"PATH 长度：{len(os.environ.get('PATH', ''))}")

# 检查 PATH 中是否包含 npm/npx
path_dirs = os.environ.get('PATH', '').split(os.pathsep)
npm_found = False
npx_path = None

for dir_path in path_dirs:
    if 'npm' in dir_path.lower() or 'node' in dir_path.lower():
        print(f"  ✓ 发现 Node.js 相关路径：{dir_path}")
        npm_found = True
        
        # 检查 npx 是否存在
        npx_exe = os.path.join(dir_path, 'npx.cmd')
        if os.path.exists(npx_exe):
            npx_path = npx_exe
            print(f"    ✓ 找到 npx.cmd: {npx_exe}")
        
        npm_exe = os.path.join(dir_path, 'npm.cmd')
        if os.path.exists(npm_exe):
            print(f"    ✓ 找到 npm.cmd: {npm_exe}")

if not npm_found:
    print("  ⚠️ 警告：PATH 中没有发现 Node.js/npm 相关路径！")

# ============================================================================
# 步骤 3: 检查 npx/npm 是否可用
# ============================================================================

print(f"\n【步骤 3】检查 npx/npm 可用性")

def run_command(cmd, description, env=None):
    """执行命令并输出详细结果"""
    print(f"\n  执行：{description}")
    print(f"  命令：{cmd}")
    
    if env is None:
        env = os.environ.copy()
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=False,  # 先捕获原始字节
            timeout=60,
            env=env
        )
        
        print(f"  返回码：{result.returncode}")
        
        # 尝试多种编码解码
        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'cp936', 'latin-1']
        
        for encoding in encodings_to_try:
            try:
                stdout_decoded = result.stdout.decode(encoding, errors='replace')
                stderr_decoded = result.stderr.decode(encoding, errors='replace')
                
                if encoding == 'utf-8':
                    print(f"  [UTF-8 解码]")
                else:
                    print(f"  [{encoding.upper()} 解码尝试]")
                
                if stdout_decoded.strip():
                    print(f"    STDOUT ({len(stdout_decoded)} 字符):")
                    stdout_lines = stdout_decoded.strip().split('\n')[:10]  # 只显示前 10 行
                    for line in stdout_lines:
                        print(f"      {line}")
                    if len(stdout_decoded.strip().split('\n')) > 10:
                        print(f"      ... (共 {len(stdout_decoded.strip().split(chr(10)))} 行)")
                
                if stderr_decoded.strip():
                    print(f"    STDERR ({len(stderr_decoded)} 字符):")
                    stderr_lines = stderr_decoded.strip().split('\n')[:10]
                    for line in stderr_lines:
                        print(f"      {line}")
                    if len(stderr_decoded.strip().split('\n')) > 10:
                        print(f"      ... (共 {len(stderr_decoded.strip().split(chr(10)))} 行)")
                
                # 如果是 UTF-8 解码成功且没有乱码特征，标记为成功
                if encoding == 'utf-8' and '' not in stdout_decoded and '' not in stderr_decoded:
                    print(f"  ✓ UTF-8 解码成功，无乱码")
                    return result, stdout_decoded, stderr_decoded
                    
            except Exception as e:
                print(f"  {encoding} 解码失败：{e}")
        
        return result, None, None
        
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 命令执行超时 (60 秒)")
        return None, None, None
    except Exception as e:
        print(f"  ⚠️ 命令执行异常：{e}")
        return None, None, None

# 3.1 检查 npx 版本
print("\n  --- 3.1 检查 npx 版本 ---")
run_command("npx --version", "npx --version")

# 3.2 检查 npm 版本  
print("\n  --- 3.2 检查 npm 版本 ---")
run_command("npm --version", "npm --version")

# 3.3 检查 apifox CLI 是否安装
print("\n  --- 3.3 检查 apifox CLI ---")
run_command("npx apifox --version", "npx apifox --version")

# ============================================================================
# 步骤 4: 执行实际的 Apifox CLI 命令（带详细日志）
# ============================================================================

print(f"\n【步骤 4】执行实际 Apifox CLI 命令")

if not APIFOX_ACCESS_TOKEN:
    print("  ⚠️ APIFOX_ACCESS_TOKEN 为空，无法执行测试")
    sys.exit(1)

if not APIFOX_PROJECT_ID:
    print("  ⚠️ APIFOX_PROJECT_ID 为空，无法执行测试")
    sys.exit(1)

import tempfile

with tempfile.TemporaryDirectory() as temp_dir:
    cmd = (
        f"npx apifox run "
        f"--test-suite {TEST_SUITE_ID} "
        f"--access-token {APIFOX_ACCESS_TOKEN} "
        f"--project {APIFOX_PROJECT_ID} "
        f"-r json "
        f"--verbose "
        f"--out-dir {temp_dir}"
    )
    
    print(f"命令：{cmd[:200]}...")
    print(f"(为安全考虑，令牌已部分隐藏：{APIFOX_ACCESS_TOKEN[:10]}...)")
    
    # 准备环境变量（模拟定时任务环境）
    exec_env = os.environ.copy()
    exec_env['PYTHONIOENCODING'] = 'utf-8'
    exec_env['PYTHONUTF8'] = '1'
    
    # 如果是 Windows，确保使用 UTF-8 代码页
    if sys.platform == 'win32':
        exec_env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    
    result, stdout_decoded, stderr_decoded = run_command(cmd, "Apifox CLI 执行测试", env=exec_env)
    
    if result is None:
        print("\n⚠️ 命令执行失败，无法获取结果")
        sys.exit(1)
    
    # 检查返回码
    print(f"\n【执行结果】")
    print(f"返回码：{result.returncode}")
    
    if result.returncode == 0:
        print("✓ CLI 执行成功！")
        
        # 检查是否生成了报告文件
        import glob
        json_files = glob.glob(os.path.join(temp_dir, "**", "*.json"), recursive=True)
        print(f"生成的 JSON 报告文件数：{len(json_files)}")
        
        if json_files:
            print(f"报告文件：{json_files[0]}")
            try:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    report = json.load(f)
                print(f"报告解析成功！")
                stats = report.get("result", {}).get("stats", {})
                print(f"测试结果统计：{json.dumps(stats, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"报告解析失败：{e}")
    else:
        print("✗ CLI 执行失败！")
        
        # 尝试从错误信息中提取关键信息
        if stderr_decoded:
            error_lines = stderr_decoded.strip().split('\n')
            print("\n【错误分析】")
            for i, line in enumerate(error_lines[:20]):
                # 查找常见的错误模式
                if 'permission' in line.lower() or '权限' in line.lower():
                    print(f"  ⚠️ 第 {i+1} 行：发现权限错误 -> {line}")
                elif 'token' in line.lower() or 'authentication' in line.lower():
                    print(f"  ⚠️ 第 {i+1} 行：发现认证错误 -> {line}")
                elif 'project' in line.lower() and 'not found' in line.lower():
                    print(f"  ⚠️ 第 {i+1} 行：发现项目不存在错误 -> {line}")
                elif 'npx' in line.lower() or 'npm' in line.lower():
                    print(f"  ⚠️ 第 {i+1} 行：发现 npx/npm 错误 -> {line}")

# ============================================================================
# 步骤 5: 总结
# ============================================================================

print("\n" + "=" * 80)
print("调试脚本执行完毕")
print("=" * 80)
print("\n【建议操作】")
print("1. 如果 npx 命令找不到：需要在定时任务中设置完整的 PATH 环境变量")
print("2. 如果出现权限错误：检查 Token 是否有效，项目 ID 是否正确")
print("3. 如果出现编码问题：确保定时任务使用 UTF-8 编码执行")
print("\n请将以上输出保存并发送以获取进一步帮助。")
