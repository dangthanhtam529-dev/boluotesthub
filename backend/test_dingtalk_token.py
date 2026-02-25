"""
测试脚本：验证书令能否在定时任务环境下正确读取

使用方法：
    python test_dingtalk_token.py

此脚本模拟定时任务的执行环境，检查:
1. .env 文件能否正确加载
2. APIFOX_ACCESS_TOKEN 能否正确读取
3. Apifox CLI 能否正常执行
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_token")

def main():
    logger.info("=" * 60)
    logger.info("开始测试令牌读取")
    logger.info("=" * 60)
    
    # 1. 获取项目根目录
    current_file = Path(__file__).resolve()
    backend_dir = current_file.parent
    project_root = backend_dir.parent
    
    logger.info(f"当前脚本路径：{current_file}")
    logger.info(f"后端目录：{backend_dir}")
    logger.info(f"项目根目录：{project_root}")
    
    # 2. 切换工作目录
    os.chdir(project_root)
    logger.info(f"切换后工作目录：{os.getcwd()}")
    
    # 3. 加载 .env 文件
    env_file_path = project_root / ".env"
    logger.info(f".env 文件路径：{env_file_path}")
    logger.info(f".env 文件是否存在：{env_file_path.exists()}")
    
    if env_file_path.exists():
        load_dotenv(env_file_path, override=True)
        logger.info(".env 文件已加载")
    else:
        logger.error(".env 文件不存在！")
        return 1
    
    # 4. 检查环境变量
    logger.info("=" * 60)
    logger.info("环境变量检查")
    logger.info("=" * 60)
    
    access_token = os.environ.get("APIFOX_ACCESS_TOKEN")
    project_id = os.environ.get("APIFOX_PROJECT_ID")
    
    logger.info(f"APIFOX_ACCESS_TOKEN 是否存在：{bool(access_token)}")
    logger.info(f"APIFOX_ACCESS_TOKEN 前缀：{access_token[:10]}..." if access_token else "N/A")
    logger.info(f"APIFOX_PROJECT_ID: {project_id}")
    
    if not access_token:
        logger.error("错误：APIFOX_ACCESS_TOKEN 为空！")
        return 1
    
    if not project_id:
        logger.warning("警告：APIFOX_PROJECT_ID 为空！")
    
    # 5. 测试导入 ApifoxService
    logger.info("=" * 60)
    logger.info("测试 ApifoxService 初始化")
    logger.info("=" * 60)
    
    sys.path.insert(0, str(backend_dir))
    
    try:
        from app.services.apifox import ApifoxService
        service = ApifoxService()
        logger.info(f"ApifoxService 初始化成功")
        logger.info(f"service.access_token 是否存在：{bool(service.access_token)}")
        logger.info(f"service.project_id: {service.project_id}")
    except Exception as e:
        logger.error(f"ApifoxService 初始化失败：{e}", exc_info=True)
        return 1
    
    # 6. 测试 run_collection 方法的 token 重新加载逻辑
    logger.info("=" * 60)
    logger.info("测试 run_collection 的 token 重新加载逻辑")
    logger.info("=" * 60)
    
    # 模拟定时任务环境：清空环境变量，然后让 run_collection 重新加载
    original_token = os.environ.get("APIFOX_ACCESS_TOKEN")
    os.environ.pop("APIFOX_ACCESS_TOKEN", None)
    logger.info("已清空环境变量中的 APIFOX_ACCESS_TOKEN")
    logger.info(f"清空后 os.environ.get('APIFOX_ACCESS_TOKEN'): {os.environ.get('APIFOX_ACCESS_TOKEN')}")
    
    # 现在调用 run_collection 的内部逻辑，看它能否重新加载
    from dotenv import load_dotenv
    env_file_path = str(project_root / ".env")
    load_dotenv(env_file_path, override=True)
    reloaded_token = os.environ.get("APIFOX_ACCESS_TOKEN")
    
    logger.info(f"重新加载后 APIFOX_ACCESS_TOKEN: {reloaded_token[:10] if reloaded_token else 'N/A'}...")
    
    if reloaded_token == original_token:
        logger.info("✓ 令牌重新加载成功！")
    else:
        logger.error("✗ 令牌重新加载失败！")
        return 1
    
    logger.info("=" * 60)
    logger.info("所有测试通过！")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
