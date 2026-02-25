"""

Apifox CLI 服务模块 (Apifox CLI Service)



本模块封装了 Apifox CLI 的调用，提供�?

1. 测试集合执行

2. 测试报告解析

3. 项目信息获取

4. �?Apifox API 的集�?



Apifox 集成架构�?

┌─────────────────────────────────────────────────────────────�?

�?                   测试执行流程                              �?

├─────────────────────────────────────────────────────────────�?

�? 1. 前端发起执行请求                                         �?

�?    POST /api/v1/executions/                                �?

�?    { "collection_id": "xxx", "environment_id": "yyy" }     �?

├─────────────────────────────────────────────────────────────�?

�? 2. 后端创建执行记录                                         �?

�?    - MySQL: 创建 TestExecution 记录                        �?

�?    - 状�? PENDING �?RUNNING                               �?

├─────────────────────────────────────────────────────────────�?

�? 3. 调用 Apifox CLI                                         �?

�?    npx apifox run --test-suite <id> -e <env> -r json      �?

�?    - 执行测试集合                                           �?

�?    - 生成 JSON 报告                                         �?

├─────────────────────────────────────────────────────────────�?

�? 4. 解析报告并保�?                                          �?

�?    - 解析统计数据（通过/失败/耗时�?                        �?

�?    - MySQL: 更新执行记录                                    �?

�?    - MongoDB: 保存完整报告                                  �?

├─────────────────────────────────────────────────────────────�?

�? 5. 返回执行结果                                             �?

�?    { "id": "xxx", "status": "completed", ... }             �?

└─────────────────────────────────────────────────────────────�?



CLI 命令格式�?

    npx apifox run --test-suite <suite_id> --project <project_id> -e <env_id> -r json



支持的集合类型：

- test-suite: 测试套件（多�?API 测试�?

- test-scenario: 测试场景（按顺序执行的流程）

- test-scenario-folder: 测试场景文件�?

"""



from __future__ import annotations



import json

import logging

import subprocess

import tempfile

from pathlib import Path

from typing import Any



from sqlmodel import Session



from app.core.config import settings

from app.models.base import get_datetime_china

from app.models.execution import ExecutionStatus, TestExecution



# ============================================================================

# 日志配置

# ============================================================================

# 使用专门�?logger 记录 Apifox 相关日志

logger = logging.getLogger("app.apifox")





# ============================================================================

# 自定义异�?

# ============================================================================

class ApifoxCliError(Exception):

    """

    Apifox CLI 执行错误

    

    �?CLI 执行失败时抛出此异常，包括：

    - CLI 命令执行失败

    - 超时

    - 报告解析失败

    - 配置错误（如缺少令牌�?

    """

    pass





# ============================================================================

# Apifox 服务�?

# ============================================================================

class ApifoxService:

    """

    Apifox CLI 服务

    

    封装了与 Apifox 的所有交互，包括�?

    1. 执行测试集合（通过 CLI�?

    2. 解析测试报告

    3. 获取项目和集合信息（通过 API�?

    

    使用方式�?

        # 直接使用全局实例

        from app.services.apifox import apifox_service

        

        # 执行测试

        report = apifox_service.run_collection("collection_id")

        

        # 解析报告

        parsed = apifox_service.parse_report(report)

    

    配置依赖�?

    - APIFOX_ACCESS_TOKEN: Apifox 访问令牌

    - APIFOX_PROJECT_ID: 默认项目 ID

    """

    

    def __init__(self):

        """

        初始?Apifox 服务

        

        从配置中读取默认值：

        - cli_command: CLI 命令前缀（默?npx apifox?

        - access_token: 访问令牌

        - project_id: 默认项目 ID

        """

        import os
        
        # 关键修复：定时任务环境下 settings 可能读取不到 .env，需要直接从环境变量获取
        self.cli_command = "npx apifox"
        
        # 优先从环境变量直接获取，确保定时任务环境下也能读取到
        self.access_token = os.environ.get("APIFOX_ACCESS_TOKEN") or settings.APIFOX_ACCESS_TOKEN
        self.project_id = os.environ.get("APIFOX_PROJECT_ID") or settings.APIFOX_PROJECT_ID
        
        logger.info(f"ApifoxService 初始化 - access_token 是否存在：{bool(self.access_token)}, project_id: {self.project_id}")



    @staticmethod

    def _mask_token(text: str, token: str | None) -> str:

        """

        隐藏日志中的令牌

        

        安全措施：确保令牌不会出现在日志中�?

        

        Args:

            text: 原始文本

            token: 要隐藏的令牌

        

        Returns:

            隐藏令牌后的文本

        

        示例�?

            >>> _mask_token("token=abc123", "abc123")

            'token=***'

        """

        if not token:

            return text

        return text.replace(token, "***")



    def run_collection(

        self,

        collection_id: str,

        environment_id: str | None = None,

        timeout: int = 300,

        access_token: str | None = None,

        project_id: str | None = None,

        collection_type: str = "test-suite",

    ) -> dict[str, Any]:

        """

        执行 Apifox 测试集合

        

        这是核心执行方法，通过调用 Apifox CLI 来运行测试?

        

        Args:

            collection_id: 集合 ID（测试套件或场景?ID?

            environment_id: 环境 ID（可选，指定测试环境?

            timeout: 超时时间（秒），默认 300 ?

            access_token: 访问令牌（可选，覆盖默认配置?

            project_id: 项目 ID（可选，覆盖默认配置?

            collection_type: 集合类型

                - "test-suite": 测试套件

                - "test-scenario": 测试场景

                - "test-scenario-folder": 测试场景文件?

        

        Returns:

            dict: CLI 返回?JSON 报告

        

        Raises:

            ApifoxCliError: CLI 执行失败或超?

        

        执行流程?

        1. 构建命令行参?

        2. 创建临时目录存放报告

        3. 执行 CLI 命令

        4. 读取生成?JSON 报告

        5. 返回报告数据

        

        CLI 命令示例?

            npx apifox run --test-suite 12345 --project 67890 -e dev -r json --verbose --out-dir /tmp/xxx

        

        报告文件位置?

            CLI 会在 --out-dir 指定的目录下生成 JSON 报告文件

        """

        # 关键修复：定时任务环境下，每次执行前都强制从 .env 文件读取最新的 token
        # 因为 apifox_service 全局实例是在模块导入时创建的，此时 .env 可能还未加载
        # 或者环境变量中可能有旧值，需要强制覆盖
        import os
        from dotenv import load_dotenv
        
        # 获取项目根目录
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.dirname(current_file)
        app_dir = os.path.dirname(backend_dir)
        project_root = os.path.dirname(app_dir)
        env_file_path = os.path.join(project_root, ".env")
        
        # 总是重新加载 .env 文件，确保获取最新的 token
        logger.info(f"run_collection 重新加载 .env 文件：{env_file_path}")
        load_dotenv(env_file_path, override=True, verbose=True)
        
        # 强制从环境变量获取最新的 token 和 project_id
        token = os.environ.get("APIFOX_ACCESS_TOKEN")
        pid = os.environ.get("APIFOX_PROJECT_ID")
        
        # 如果传入的 access_token/project_id 不为空，优先使用传入的值
        if access_token:
            token = access_token
        if project_id:
            pid = project_id
        
        logger.info(f"run_collection 重新加载后 - token 是否存在：{bool(token)}, token 前缀：{token[:15] if token else 'N/A'}..., project_id: {pid}")



        # ====================================================================

        # 构建命令

        # ====================================================================

        cmd_parts = [self.cli_command, "run"]

        

        # 根据集合类型添加不同的参�?

        if collection_type == "test-suite":

            cmd_parts.extend(["--test-suite", collection_id])

        elif collection_type == "test-scenario":

            cmd_parts.extend(["-t", collection_id])

        elif collection_type == "test-scenario-folder":

            cmd_parts.extend(["--test-scenario-folder", collection_id])

        else:

            # 默认使用 test-suite

            cmd_parts.extend(["--test-suite", collection_id])



        # 添加认证令牌

        if token:

            cmd_parts.extend(["--access-token", token])



        # 添加项目 ID

        if pid:

            cmd_parts.extend(["--project", pid])



        # 添加环境 ID

        if environment_id:

            cmd_parts.extend(["-e", environment_id])

        

        # 添加 reporters 参数（输�?JSON 格式�?

        cmd_parts.extend(["-r", "json"])



        # 添加 verbose 参数以获取详细的执行结果

        cmd_parts.append("--verbose")



        # ====================================================================
        # 执行命令
        # ====================================================================
        # 使用临时目录存放报告文件
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd_parts.extend(["--out-dir", temp_dir])

            cmd = " ".join(cmd_parts)

            try:
                # 关键日志：记录 token 状态，便于排查定时任务环境问题
                logger.info(
                    f"Apifox CLI 执行前检查 - token 是否存在：{bool(token)}, project_id: {pid}, 当前工作目录：{os.getcwd()}"
                )
                
                if not token:
                    logger.error("Apifox CLI 执行失败：缺少 access_token，请检查 .env 文件或环境变量配置")
                    raise ApifoxCliError("缺少 Apifox access_token，请检查配置")
                
                if not pid:
                    logger.error("Apifox CLI 执行失败：缺少 project_id，请检查 .env 文件或环境变量配置")
                    raise ApifoxCliError("缺少 Apifox project_id，请检查配置")

                # 记录执行开始日志
                logger.info(f"[DEBUG] Apifox CLI 命令参数 - collection_type: {collection_type}, collection_id: {collection_id}, environment_id: {environment_id}, project_id: {pid}, cmd_parts: {cmd_parts}")
                
                logger.info(
                    "apifox_run_started",
                    extra={
                        "collection_type": collection_type,
                        "collection_id": collection_id,
                        "environment_id": environment_id,
                        "project_id": pid,
                        "timeout_sec": timeout,
                        "cmd": self._mask_token(cmd, token),
                        "cmd_parts": cmd_parts,
                    },
                )

                

                # 执行命令

                # subprocess.run 会等待命令完?

                # capture_output=True 捕获 stdout ?stderr
                
                # 关键修复：定时任务环境下需要传递完整的环境变量
                # 获取当前环境变量，并确保包含正确的 PATH
                exec_env = os.environ.copy()
                
                # 确保 UTF-8 编码
                exec_env['PYTHONIOENCODING'] = 'utf-8'
                exec_env['PYTHONUTF8'] = '1'
                # 关键修复：设置控制台代码页为 UTF-8，防止 CLI 输出乱码
                exec_env['PYTHONLEGACYWINDOWSSTDIO'] = '0'

                # 关键修复：不使用 text=True 和 encoding，而是捕获原始字节后智能解码
                # 因为 Windows 定时任务的代码页是 GBK，CLI 输出可能是 GBK 或 UTF-8
                result = subprocess.run(

                    cmd,

                    shell=True,

                    capture_output=True,  # 捕获原始字节

                    timeout=timeout,
                    
                    env=exec_env,  # 传递完整的环境变量

                )
                
                # 智能解码：尝试 UTF-8，失败则尝试 GBK
                def smart_decode(data: bytes) -> str:
                    if not data:
                        return ""
                    # 先尝试 UTF-8
                    try:
                        return data.decode('utf-8')
                    except UnicodeDecodeError:
                        pass
                    # 再尝试 GBK
                    try:
                        return data.decode('gbk')
                    except UnicodeDecodeError:
                        pass
                    # 最后使用 replace 模式
                    return data.decode('utf-8', errors='replace')
                
                stdout_full = smart_decode(result.stdout)
                stderr_full = smart_decode(result.stderr)



                # 记录失败日志

                if result.returncode != 0:
                    # 关键修复：记录完整的 stderr 和 stdout，便于排查问题
                    # stdout_full 和 stderr_full 已经在上面智能解码
                    masked_stderr = self._mask_token(stderr_full, token)
                    masked_stdout = self._mask_token(stdout_full, token)
                    
                    # 使用 logger.error 直接记录完整错误到日志文件
                    logger.error(f"Apifox CLI 执行失败 - returncode: {result.returncode}")
                    logger.error(f"stderr: {masked_stderr[:5000]}")
                    logger.error(f"stdout: {masked_stdout[:5000]}")
                    
                    # 同时打印到控制台，便于立即查看
                    print(f"[ERROR] Apifox CLI 执行失败 - returncode: {result.returncode}")
                    print(f"[ERROR] stderr: {masked_stderr[:2000]}")
                    print(f"[ERROR] stdout: {masked_stdout[:2000]}")



                # 记录详细输出（调试用?

                if stdout_full:

                    logger.debug(

                        "apifox_run_stdout",

                        extra={"stdout": self._mask_token(stdout_full, token)[:4000]},

                    )



                # ====================================================================

                # 读取报告文件

                # ====================================================================

                # CLI 会在 out-dir 下生�?JSON 报告文件

                import glob

                json_files = glob.glob(

                    str(Path(temp_dir) / "**" / "*.json"),

                    recursive=True,

                )

                

                if json_files:

                    # 按文件大小排序，选择最大的（通常是主报告�?

                    json_files.sort(key=lambda p: Path(p).stat().st_size, reverse=True)

                    logger.info(

                        "apifox_report_file_found",

                        extra={"report_file": json_files[0], "candidates": len(json_files)},

                    )

                    with open(json_files[0], "r", encoding="utf-8") as f:

                        report = json.load(f)

                    logger.info(

                        "apifox_run_finished",

                        extra={

                            "collection_type": collection_type,

                            "collection_id": collection_id,

                            "environment_id": environment_id,

                            "project_id": pid,

                            "return_code": result.returncode,

                        },

                    )

                    return report

                else:

                    # 如果没有文件，尝试从 stdout 解析

                    try:

                        report = json.loads(stdout_full)

                        logger.info(

                            "apifox_run_finished",

                            extra={

                                "collection_type": collection_type,

                                "collection_id": collection_id,

                                "environment_id": environment_id,

                                "project_id": pid,

                                "return_code": result.returncode,

                            },

                        )

                        return report

                    except json.JSONDecodeError:

                        if result.returncode != 0:

                            error_msg = stderr_full.strip() if stderr_full else "CLI 返回非 0 且未产出 JSON 报告文件"

                            raise ApifoxCliError(f"CLI 执行失败：{error_msg}")

                        raise ApifoxCliError(f"无法找到 JSON 报告文件，stdout: {stdout_full[:500]}")

            except subprocess.TimeoutExpired:
                raise ApifoxCliError(f"执行超时（{timeout}秒）")



    def parse_report(self, report: dict[str, Any]) -> dict[str, Any]:

        """

        解析 Apifox 测试报告

        

        �?CLI 返回的原�?JSON 报告转换为结构化的执行结果�?

        

        Args:

            report: CLI 返回的原始报�?

        

        Returns:

            解析后的执行结果，包含：

            - total_cases: 总用例数

            - passed_cases: 通过�?

            - failed_cases: 失败�?

            - duration: 执行时长（秒�?

            - success_rate: 成功率（百分比）

            - failed_details: 失败详情列表

            - execution_details: 每个用例的执行详�?

            - raw_report: 原始报告（用于存储）

        

        报告结构说明�?

            {

                "result": {

                    "stats": {

                        "steps": { "total": 10, "passed": 8, "failed": 2 },

                        "requests": { "total": 10, "failed": 2 },

                        "timings": { "started": 123, "completed": 456 }

                    },

                    "failures": [

                        { "error": { "name": "...", "message": "..." } }

                    ],

                    "executions": [

                        { "item": {...}, "response": {...}, "passed": true }

                    ]

                }

            }

        """

        result_data = report.get("result", {})

        stats = result_data.get("stats", {})

        timings = result_data.get("timings", {})



        # ====================================================================

        # 解析统计数据

        # ====================================================================

        steps_stats = stats.get("steps", {})

        requests_stats = stats.get("requests", {})



        # 优先使用 steps 统计

        total = steps_stats.get("total", 0)

        passed = steps_stats.get("passed", 0)

        failed = steps_stats.get("failed", 0)



        # 如果 steps 为空，尝试使�?tests 统计

        if total == 0:

            tests_stats = stats.get("tests", {})

            total = tests_stats.get("total", 0)

            failed = tests_stats.get("failed", 0)

            passed = total - failed - tests_stats.get("pending", 0)



        # 如果 tests 也为空，使用 requests 统计

        if total == 0:

            total = requests_stats.get("total", 0)

            failed = requests_stats.get("failed", 0)

            passed = total - failed - requests_stats.get("pending", 0)



        # ====================================================================

        # 解析执行时长

        # ====================================================================

        started = timings.get("started", 0)

        completed = timings.get("completed", 0)

        duration_ms = completed - started if started and completed else 0

        duration_sec = duration_ms / 1000 if duration_ms else None



        # ====================================================================

        # 解析失败详情

        # ====================================================================

        failed_cases = []

        failures = result_data.get("failures", [])

        for failure in failures:

            error_info = failure.get("error", {})

            cursor = failure.get("cursor", {})

            failed_cases.append({

                "name": error_info.get("test", "未知"),

                "error": error_info.get("name", ""),

                "message": error_info.get("message", ""),

                "ref": cursor.get("ref", ""),

            })



        # ====================================================================

        # 解析执行详情

        # ====================================================================

        executions = result_data.get("executions", [])

        execution_details = []

        for ex in executions:

            item = ex.get("item", {})

            req = item.get("request", {})

            url = req.get("url", {})

            path_parts = url.get("path", [])

            api_path = "/" + "/".join([str(p) for p in path_parts if p]) if path_parts else ""



            resp = ex.get("response", {})

            status_code = resp.get("code") if isinstance(resp, dict) else None



            rv = ex.get("responseValidation", {})

            schema_valid = rv.get("schema", {}).get("valid", True) if rv else True

            code_valid = rv.get("responseCode", {}).get("valid", True) if rv else True



            execution_details.append({

                "name": item.get("name", "未知"),

                "api_path": api_path,

                "method": req.get("method", ""),

                "status_code": status_code,

                "response_time": ex.get("responseTime"),

                "passed": ex.get("passed", True),

                "schema_valid": schema_valid,

                "code_valid": code_valid,

            })



        return {

            "total_cases": total,

            "passed_cases": passed,

            "failed_cases": failed,

            "skipped_cases": 0,

            "duration": duration_sec,

            "success_rate": (passed / total * 100) if total > 0 else 0,

            "failed_details": failed_cases,

            "execution_details": execution_details,

            "raw_report": report,

        }



    async def execute_and_save(

        self,

        session: Session,

        execution: TestExecution,

        collection_id: str,

        environment_id: str | None = None,

        collection_type: str = "test-suite",

        access_token: str | None = None,

        project_id: str | None = None,

    ) -> TestExecution:

        """

        执行测试并保存结?

        

        这是完整的执行流程方法，包括?

        1. 更新状态为执行?

        2. 调用 CLI 执行测试

        3. 解析报告

        4. 保存?MySQL ?MongoDB

        5. 更新执行记录

        

        Args:

            session: 数据库会?

            execution: 执行记录（已创建?

            collection_id: 集合 ID

            environment_id: 环境 ID

            collection_type: 集合类型

            access_token: Apifox Access Token（可选）

            project_id: Apifox 项目 ID（可选）

        

        Returns:

            更新后的执行记录

        

        数据存储策略?

        - MySQL: 存储执行元数据（状态、统计、摘要）

        - MongoDB: 存储完整报告（大数据量）

        

        错误处理?

        - CLI 执行失败：记录错误信息，状态设?FAILED

        - MongoDB 保存失败：回退?MySQL 存储

        """

        from app.services.mongodb_report import MongoDBReportService
        
        # 关键修复：定时任务环境下，强制从 .env 文件读取最新的 token
        import os
        from dotenv import load_dotenv
        
        # 获取项目根目录
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.dirname(current_file)
        app_dir = os.path.dirname(backend_dir)
        project_root = os.path.dirname(app_dir)
        env_file_path = os.path.join(project_root, ".env")
        
        # 总是重新加载 .env 文件
        logger.info(f"execute_and_save 重新加载 .env 文件：{env_file_path}")
        load_dotenv(env_file_path, override=True, verbose=True)
        
        # 强制从环境变量获取最新的 token 和 project_id
        env_token = os.environ.get("APIFOX_ACCESS_TOKEN")
        env_project_id = os.environ.get("APIFOX_PROJECT_ID")
        
        # 优先使用传入的值，如果没有则使用环境变量的值
        if not access_token:
            access_token = env_token
        if not project_id:
            project_id = env_project_id
        
        logger.info(f"execute_and_save 重新加载后 - token 是否存在：{bool(access_token)}, token 前缀：{access_token[:15] if access_token else 'N/A'}..., project_id: {project_id}")
        
        try:

            # ====================================================================

            # 更新状态为执行�?

            # ====================================================================

            execution.status = ExecutionStatus.RUNNING

            execution.started_at = get_datetime_china()

            session.commit()



            # ====================================================================

            # 执行测试

            # ====================================================================

            report = self.run_collection(

                collection_id, 

                environment_id, 

                collection_type=collection_type,

                access_token=access_token,

                project_id=project_id,

            )



            # ====================================================================

            # 解析报告

            # ====================================================================

            parsed = self.parse_report(report)



            # ====================================================================

            # 更新执行记录（MySQL�?

            # ====================================================================

            execution.status = ExecutionStatus.COMPLETED

            execution.completed_at = get_datetime_china()

            execution.total_cases = parsed["total_cases"]

            execution.passed_cases = parsed["passed_cases"]

            execution.failed_cases = parsed["failed_cases"]

            execution.duration = parsed["duration"]

            

            # 提取性能指标

            result_data = report.get("result", {})

            timings = result_data.get("timings", {})

            execution.response_time_avg = timings.get("responseAverage")

            execution.response_time_max = timings.get("responseMax")

            execution.response_time_min = timings.get("responseMin")

            

            # 提取错误摘要（前 200 字符�?

            failed_details = parsed.get("failed_details", [])

            if failed_details:

                error_msg = failed_details[0].get("message", "")[:200]

                execution.error_summary = error_msg

            

            # ====================================================================

            # 保存完整报告�?MongoDB

            # ====================================================================

            try:

                report_size_bytes = len(json.dumps(report, ensure_ascii=False).encode("utf-8"))

                logger.info(

                    "mongodb_report_save_started",

                    extra={

                        "execution_id": str(execution.id),

                        "size_bytes": report_size_bytes,

                    },

                )

                

                mongo_id = await MongoDBReportService.save_report(

                    execution_id=str(execution.id),

                    apifox_collection_id=collection_id,

                    project_name=execution.project_name or "",

                    environment=environment_id or "",

                    report_data=report,

                )

                

                logger.info(

                    "mongodb_report_save_ok",

                    extra={

                        "execution_id": str(execution.id),

                        "mongo_report_id": mongo_id,

                    },

                )

                execution.mongo_report_id = mongo_id

                execution.has_mongodb_report = True

                # 不再保存完整 report_json �?MySQL，节省空�?

                execution.report_json = None

            except Exception as mongo_error:

                # MongoDB 保存失败，回退�?MySQL 存储

                logger.exception(

                    "mongodb_report_save_failed_fallback_to_mysql",

                    extra={"execution_id": str(execution.id)},

                )

                # 截断报告数据以适应 MySQL TEXT 字段（最大 65535 字符）

                report_str = json.dumps(report, ensure_ascii=False)

                if len(report_str) > 60000:  # 留一些余量

                    logger.warning(

                        "report_truncated_for_mysql",

                        extra={

                            "execution_id": str(execution.id),

                            "original_size": len(report_str),

                            "truncated_size": 60000,

                        },

                    )

                    # 创建截断版本的报告

                    truncated_report = {

                        "truncated": True,

                        "original_size": len(report_str),

                        "note": "报告数据过大，已截断。完整报告请检查 MongoDB 或 Apifox 平台",

                        "preview": report_str[:60000],

                    }

                    execution.report_json = json.dumps(truncated_report, ensure_ascii=False)

                else:

                    execution.report_json = report_str

                execution.has_mongodb_report = False



        except ApifoxCliError as e:

            # CLI 执行错误

            execution.status = ExecutionStatus.FAILED

            execution.completed_at = get_datetime_china()

            execution.error_message = str(e)[:500]

            execution.error_summary = str(e)[:200]

        except Exception as e:

            # 其他异常

            execution.status = ExecutionStatus.FAILED

            execution.completed_at = get_datetime_china()

            execution.error_message = f"执行异常: {str(e)}"[:500]

            execution.error_summary = f"执行异常: {str(e)}"[:200]



        session.commit()

        session.refresh(execution)

        return execution



    async def get_project_collections(

        self,

        project_id: str,

        access_token: str | None = None,

    ) -> list[dict[str, Any]]:

        """

        获取 Apifox 项目下的测试集合列表

        

        通过 Apifox CLI 获取项目中的测试套件和场景�?

        

        Args:

            project_id: Apifox 项目 ID

            access_token: 访问令牌

        

        Returns:

            测试集合列表，每个集合包含：

            - id: 集合 ID

            - name: 集合名称

            - type: 集合类型（test-suite/test-scenario�?

            - description: 描述

        

        CLI 命令�?

        - 测试套件: apifox test-suite list --project <projectId>

        - 测试场景: apifox test-scenario list --project <projectId>

        """

        token = access_token or self.access_token

        if not token:

            raise ApifoxCliError("缺少 Apifox 访问令牌")

        

        collections = []

        

        # 使用 CLI 命令获取测试套件

        try:

            cmd = f"npx apifox test-suite list --project {project_id} --access-token {token}"

            logger.info(f"执行CLI命令获取测试套件: npx apifox test-suite list --project {project_id}")

            result = subprocess.run(

                cmd,

                shell=True,

                capture_output=True,

                text=True,

                timeout=120,

                encoding="utf-8",

            )

            if result.returncode == 0 and result.stdout:

                import json

                try:

                    data = json.loads(result.stdout)

                    for item in data.get("data", []):

                        collections.append({

                            "id": str(item.get("id")),

                            "name": item.get("name"),

                            "type": "test-suite",

                            "description": item.get("description", ""),

                            "folder": item.get("folder", ""),

                        })

                    logger.info(f"获取了 {len([c for c in collections if c['type'] == 'test-suite'])} 个测试套件")
                except json.JSONDecodeError:

                    logger.warning(f"解析测试套件输出失败: {result.stdout[:500]}")

            else:

                logger.warning(f"获取测试套件失败: {result.stderr}")

        except Exception as e:

            logger.warning(f"获取测试套件异常: {e}")

        

        # 使用 CLI 命令获取测试场景

        try:

            cmd = f"npx apifox test-scenario list --project {project_id} --access-token {token}"

            logger.info(f"执行CLI命令获取测试场景: npx apifox test-scenario list --project {project_id}")

            result = subprocess.run(

                cmd,

                shell=True,

                capture_output=True,

                text=True,

                timeout=120,

                encoding="utf-8",

            )

            if result.returncode == 0 and result.stdout:

                import json

                try:

                    data = json.loads(result.stdout)

                    scenario_count = 0

                    for item in data.get("data", []):

                        collections.append({

                            "id": str(item.get("id")),

                            "name": item.get("name"),

                            "type": "test-scenario",

                            "description": item.get("description", ""),

                            "folder": item.get("folder", ""),

                        })

                        scenario_count += 1

                    logger.info(f"获取了 {scenario_count} 个测试场景")

                except json.JSONDecodeError:

                    logger.warning(f"解析测试场景输出失败: {result.stdout[:500]}")

            else:

                logger.warning(f"获取测试场景失败: {result.stderr}")

        except Exception as e:

            logger.warning(f"获取测试场景异常: {e}")

        

        return collections



    async def get_project_info(

        self,

        project_id: str,

        access_token: str | None = None,

    ) -> dict[str, Any] | None:

        """

        获取 Apifox 项目信息

        

        通过 Apifox API 获取项目详情�?

        

        Args:

            project_id: Apifox 项目 ID

            access_token: 访问令牌

        

        Returns:

            项目信息，包含：

            - id: 项目 ID

            - name: 项目名称

            - description: 项目描述

            - memberCount: 成员数量

            - apiCount: API 数量

        

        API 端点�?

            GET /api/v1/projects/{id}

        """

        import httpx

        

        token = access_token or self.access_token

        if not token:

            raise ApifoxCliError("缺少 Apifox 访问令牌")

        

        headers = {

            "X-Apifox-Api-Version": "2024-03-28",

            "Authorization": f"Bearer {token}",

        }

        

        async with httpx.AsyncClient(timeout=30) as client:

            try:

                url = f"https://api.apifox.com/api/v1/projects/{project_id}"

                response = await client.get(url, headers=headers)

                if response.status_code == 200:

                    data = response.json()

                    return data.get("data", {})

            except Exception as e:

                logger.warning(f"获取项目信息失败: {e}")

        

        return None





# ============================================================================

# 全局服务实例

# ============================================================================

# 创建全局实例，方便在应用中直接导入使�?

# 使用方式：from app.services.apifox import apifox_service

apifox_service = ApifoxService()

