"""
MongoDB 报告服务模块 (MongoDB Report Service)

本模块负责将测试报告存储到 MongoDB，并提供查询分析功能。
是测试报告数据存储的核心服务。

数据存储架构：
┌─────────────────────────────────────────────────────────────┐
│                    测试报告存储策略                          │
├─────────────────────────────────────────────────────────────┤
│  MySQL (结构化数据)                                          │
│  ├── TestExecution 表                                        │
│  │   ├── 执行元数据（状态、时间、统计）                      │
│  │   ├── mongo_report_id (关联 MongoDB)                     │
│  │   └── 性能指标摘要                                        │
│  └── 优点：事务支持、关系查询、索引高效                      │
├─────────────────────────────────────────────────────────────┤
│  MongoDB (文档数据)                                          │
│  ├── test_reports 集合                                       │
│  │   ├── 完整报告 JSON                                       │
│  │   ├── 失败用例详情                                        │
│  │   └── 性能指标                                            │
│  ├── report_summaries 集合                                   │
│  │   └── 报告摘要（用于快速查询）                            │
│  ├── report_failures 集合                                    │
│  │   └── 失败用例（用于错误分析）                            │
│  └── 优点：灵活文档结构、大数据量、聚合查询                  │
└─────────────────────────────────────────────────────────────┘

MongoDB 集合说明：
- test_reports: 主集合，存储完整报告
- report_summaries: 摘要集合，用于列表查询
- report_failures: 失败用例集合，用于错误分析
- report_requests: 请求详情集合，用于性能分析
- report_notes: 报告备注集合，用于人工标注

索引策略：
- execution_id: 唯一索引，快速关联
- apifox_collection_id: 普通索引，按集合查询
- project_id: 普通索引，按项目隔离
- created_at: 普通索引，时间范围查询
- signature: 普通索引，错误指纹匹配

使用示例：
    # 保存报告
    report_id = await MongoDBReportService.save_report(
        execution_id="xxx",
        apifox_collection_id="12345",
        project_name="API测试",
        environment="dev",
        report_data={...}
    )
    
    # 查询报告
    report = await MongoDBReportService.get_report(report_id)
    
    # 分析失败趋势
    failures = await MongoDBReportService.analyze_failures(collection_id="12345")
"""

import json
import hashlib
import logging
import re
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.mongodb import get_mongodb_db, init_mongodb

# ============================================================================
# 日志配置
# ============================================================================
logger = logging.getLogger("app.mongodb_report")

# ============================================================================
# 初始化 MongoDB 连接
# ============================================================================
# 确保在模块加载时初始化连接
# 这样后续所有操作都可以直接使用 get_mongodb_db()
init_mongodb()


class MongoDBReportService:
    """
    MongoDB 报告服务
    
    提供测试报告的存储、查询和分析功能。
    
    主要方法：
    - save_report: 保存完整报告
    - get_report: 获取报告详情
    - analyze_failures: 分析失败趋势
    - get_performance_trends: 获取性能趋势
    
    数据流程：
    1. 接收 Apifox CLI 返回的 JSON 报告
    2. 提取关键信息（统计、失败用例、性能指标）
    3. 存储到 MongoDB 各集合
    4. 建立索引以支持高效查询
    """
    
    # ========================================================================
    # 集合名称常量
    # ========================================================================
    # 主报告集合：存储完整报告
    COLLECTION_NAME = "test_reports"
    # 摘要集合：存储报告摘要，用于列表查询
    SUMMARY_COLLECTION_NAME = "report_summaries"
    # 失败用例集合：存储失败详情，用于错误分析
    FAILURES_COLLECTION_NAME = "report_failures"
    # 请求详情集合：存储每个请求的详情，用于性能分析
    REQUESTS_COLLECTION_NAME = "report_requests"
    # 备注集合：存储人工标注
    NOTES_COLLECTION_NAME = "report_notes"
    # Schema 版本：用于数据迁移
    SCHEMA_VERSION = 2

    @staticmethod
    def _build_match(*, days: int, collection_id: str | None, project_id: str | None = None) -> dict[str, Any]:
        since = datetime.utcnow() - __import__("datetime").timedelta(days=days)
        match: dict[str, Any] = {"created_at": {"$gte": since}}
        if collection_id:
            cid = collection_id.strip()
            if cid.isdigit():
                match["apifox_collection_id"] = {"$in": [cid, int(cid)]}
            else:
                match["apifox_collection_id"] = cid
        if project_id:
            match["project_id"] = project_id
        return match
    
    @staticmethod
    async def save_report(
        execution_id: str,
        apifox_collection_id: str,
        project_name: str,
        environment: str,
        report_data: dict,
        project_id: str | None = None,
    ) -> str:
        """
        保存测试报告到 MongoDB
        
        Args:
            execution_id: 执行记录 ID
            apifox_collection_id: Apifox 集合 ID
            project_name: 项目名称
            environment: 环境名称
            report_data: Apifox 返回的完整报告数据
            
        Returns:
            MongoDB 文档 ID
        """
        db = get_mongodb_db()
        collection = db[MongoDBReportService.COLLECTION_NAME]
        
        # 提取性能指标
        metrics = MongoDBReportService._extract_metrics(report_data)
        
        # 提取失败用例
        failed_cases = MongoDBReportService._extract_failed_cases(report_data)
        
        # 构建文档
        document = {
            "execution_id": execution_id,
            "apifox_collection_id": apifox_collection_id,
            "project_id": project_id,
            "project_name": project_name,
            "environment": environment,
            "report": report_data,
            "metrics": metrics,
            "failed_cases": failed_cases,
            "created_at": datetime.utcnow(),
            "size_bytes": len(json.dumps(report_data)),
            "schema_version": MongoDBReportService.SCHEMA_VERSION,
        }
        
        # 插入文档
        result = await collection.insert_one(document)
        report_id = str(result.inserted_id)
        try:
            await MongoDBReportService.upsert_derived(
                report_id=report_id,
                execution_id=execution_id,
                apifox_collection_id=apifox_collection_id,
                project_name=project_name,
                environment=environment,
                created_at=document["created_at"],
                report_data=report_data,
            )
        except Exception:
            logger.exception(
                "report_derived_upsert_failed",
                extra={"execution_id": execution_id, "report_id": report_id},
            )
        return report_id
    
    @staticmethod
    def _extract_metrics(report_data: dict) -> dict:
        """从报告中提取性能指标"""
        metrics = {
            "response_time_avg": None,
            "response_time_max": None,
            "response_time_min": None,
            "response_time_p95": None,
            "response_time_p99": None,
        }
        
        try:
            result = report_data.get("result", {})
            timings = result.get("timings", {})
            
            # 提取响应时间统计
            if "responseAverage" in timings:
                metrics["response_time_avg"] = timings["responseAverage"]
            if "responseMax" in timings:
                metrics["response_time_max"] = timings["responseMax"]
            if "responseMin" in timings:
                metrics["response_time_min"] = timings["responseMin"]
                
        except Exception:
            pass
            
        return metrics
    
    @staticmethod
    def _extract_failed_cases(report_data: dict) -> list[dict]:
        """从报告中提取失败用例"""
        failed_cases = []
        
        try:
            result = report_data.get("result", {})
            failures = result.get("failures", [])
            executions = result.get("executions", [])
            
            exec_map = {}
            for ex in executions:
                cursor_ref = (ex.get("cursor") or {}).get("ref")
                if cursor_ref:
                    exec_map[cursor_ref] = ex
            
            for failure in failures:
                error_info = failure.get("error", {})
                cursor = failure.get("cursor", {})
                ref = cursor.get("ref", "")
                
                error_message = error_info.get("message", "Unknown error")
                error_name = error_info.get("name", "")
                test_name = error_info.get("test", "Unknown")
                
                api_path = ""
                api_method = ""
                response_status = 0
                
                if ref and ref in exec_map:
                    ex = exec_map[ref]
                    item = ex.get("item", {})
                    req = item.get("request", {})
                    url = req.get("url", {})
                    path_parts = url.get("path", [])
                    if path_parts:
                        api_path = "/" + "/".join([str(p) for p in path_parts if p is not None])
                    api_method = req.get("method", "")
                    resp = ex.get("response", {})
                    if isinstance(resp, dict):
                        response_status = resp.get("code", 0)
                
                source = failure.get("source", {})
                if source:
                    if not api_path:
                        url_path = source.get("request", {}).get("url", {}).get("path", "")
                        if isinstance(url_path, list):
                            api_path = "/" + "/".join([str(p) for p in url_path if p is not None])
                        elif url_path:
                            api_path = str(url_path)
                    if not api_method:
                        api_method = source.get("request", {}).get("method", "")
                    if not response_status:
                        response_status = failure.get("response", {}).get("code", 0)
                    if not test_name or test_name == "Unknown":
                        test_name = source.get("name", "Unknown")
                
                error_norm = MongoDBReportService._normalize_error(str(error_message))
                signature = MongoDBReportService._signature(
                    api_path=str(api_path or ""),
                    api_method=str(api_method or ""),
                    response_status=int(response_status or 0),
                    error_norm=error_norm,
                )
                
                failed_case = {
                    "name": test_name,
                    "error": error_message,
                    "error_name": error_name,
                    "error_norm": error_norm,
                    "signature": signature,
                    "api_path": api_path,
                    "api_method": api_method,
                    "response_status": response_status,
                    "ref": ref,
                }
                failed_cases.append(failed_case)
                
        except Exception:
            pass
            
        return failed_cases

    @staticmethod
    def _normalize_error(text: str) -> str:
        t = text.strip().lower()
        t = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", t)
        t = re.sub(r"\b\d+\b", "<n>", t)
        t = re.sub(r"\s+", " ", t)
        return t[:300]

    @staticmethod
    def _signature(
        *,
        api_path: str,
        api_method: str,
        response_status: int,
        error_norm: str,
    ) -> str:
        raw = json.dumps(
            {
                "api_path": api_path,
                "api_method": api_method,
                "response_status": response_status,
                "error_norm": error_norm,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _extract_summary(report_data: dict) -> dict[str, Any]:
        result = report_data.get("result", {})
        stats = result.get("stats", {})
        timings = result.get("timings", {}) or {}

        steps = stats.get("steps", {}) or {}
        requests = stats.get("requests", {}) or {}
        tests = stats.get("tests", {}) or {}

        total = int(steps.get("total", 0) or 0)
        passed = int(steps.get("passed", 0) or 0)
        failed = int(steps.get("failed", 0) or 0)

        if total == 0:
            total = int(tests.get("total", 0) or 0)
            failed = int(tests.get("failed", 0) or 0)
            pending = int(tests.get("pending", 0) or 0)
            passed = max(total - failed - pending, 0)

        if total == 0:
            total = int(requests.get("total", 0) or 0)
            failed = int(requests.get("failed", 0) or 0)
            pending = int(requests.get("pending", 0) or 0)
            passed = max(total - failed - pending, 0)

        started = timings.get("started")
        completed = timings.get("completed")
        duration_ms = None
        if isinstance(started, (int, float)) and isinstance(completed, (int, float)):
            duration_ms = int(completed - started)

        return {
            "tests_total": total,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_pending": 0,
            "duration_ms": duration_ms,
            "response_time_avg": timings.get("responseAverage"),
            "response_time_min": timings.get("responseMin"),
            "response_time_max": timings.get("responseMax"),
        }

    @staticmethod
    def _fingerprint_failure(failure: dict[str, Any]) -> str:
        raw = json.dumps(
            {
                "name": failure.get("name"),
                "api_path": failure.get("api_path"),
                "api_method": failure.get("api_method"),
                "response_status": failure.get("response_status"),
                "error": failure.get("error"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _extract_requests(report_data: dict) -> list[dict[str, Any]]:
        run = report_data.get("run", {}) or {}
        result = report_data.get("result", {}) or {}
        executions = []
        if isinstance(run.get("executions"), list):
            executions = run.get("executions") or []
        elif isinstance(result.get("executions"), list):
            executions = result.get("executions") or []
        rows: list[dict[str, Any]] = []

        def _truncate_json(obj: Any, limit: int) -> Any:
            try:
                raw = json.dumps(obj, ensure_ascii=False, default=str)
            except Exception:
                return {"_error": "not_serializable"}
            if len(raw) <= limit:
                return obj
            return {"_truncated": True, "preview": raw[: limit // 2]}

        def _headers_to_dict(headers: Any) -> dict[str, Any] | None:
            if not isinstance(headers, list):
                return None
            out: dict[str, Any] = {}
            for h in headers:
                if not isinstance(h, dict):
                    continue
                k = h.get("key")
                v = h.get("value")
                if isinstance(k, str) and k:
                    out[k] = v
            return out or None

        for ex in executions:
            request_exec_id = (ex or {}).get("id")
            item = (ex or {}).get("item", {}) or {}
            req = item.get("request", {}) or {}
            url = req.get("url", {}) or {}
            path_parts = url.get("path")
            api_path = None
            if isinstance(path_parts, list):
                api_path = "/" + "/".join([str(p) for p in path_parts if p is not None])
            method = req.get("method")
            request_headers = _headers_to_dict(req.get("header"))
            request_body = req.get("body")
            request_query = url.get("query")
            protocol = url.get("protocol")
            host = url.get("host")
            full_url = None
            if isinstance(host, list) and host and api_path:
                full_url = f"{protocol or 'http'}://{'.'.join([str(h) for h in host if h is not None])}{api_path}"

            status_code = None
            resp = (ex or {}).get("response")
            if isinstance(resp, dict) and "code" in resp:
                status_code = resp.get("code")
            elif isinstance(resp, list) and resp:
                first = resp[0]
                if isinstance(first, dict) and "code" in first:
                    status_code = first.get("code")

            latency_ms = None
            if "responseTime" in ex:
                latency_ms = ex.get("responseTime")
            if latency_ms is None:
                if isinstance(resp, dict) and "responseTime" in resp:
                    latency_ms = resp.get("responseTime")
                elif isinstance(resp, list) and resp and isinstance(resp[0], dict) and "responseTime" in resp[0]:
                    latency_ms = resp[0].get("responseTime")
            response_size = (ex or {}).get("responseSize")
            if response_size is None:
                if isinstance(resp, dict) and "responseSize" in resp:
                    response_size = resp.get("responseSize")
                elif isinstance(resp, list) and resp and isinstance(resp[0], dict) and "responseSize" in resp[0]:
                    response_size = resp[0].get("responseSize")
            passed = (ex or {}).get("passed")

            schema_valid = None
            code_valid = None
            rv = (ex or {}).get("responseValidation")
            if isinstance(rv, dict):
                schema = rv.get("schema")
                if isinstance(schema, dict) and "valid" in schema:
                    schema_valid = schema.get("valid")
                resp_code = rv.get("responseCode")
                if isinstance(resp_code, dict) and "valid" in resp_code:
                    code_valid = resp_code.get("valid")

            rows.append(
                {
                    "request_exec_id": request_exec_id,
                    "api_path": api_path,
                    "method": method,
                    "full_url": full_url,
                    "request_headers": _truncate_json(request_headers, 4000) if request_headers else None,
                    "request_query": _truncate_json(request_query, 4000) if request_query else None,
                    "request_body": _truncate_json(request_body, 8000) if request_body else None,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "response_size": response_size,
                    "passed": passed,
                    "schema_valid": schema_valid,
                    "code_valid": code_valid,
                    "name": item.get("name"),
                }
            )
        return rows

    @staticmethod
    def _extract_expected_status_codes(report_data: dict) -> list[int]:
        col = report_data.get("collection") or {}
        seen: set[str] = set()
        codes: list[int] = []

        def _as_path(url: dict) -> str | None:
            path_parts = (url or {}).get("path")
            if isinstance(path_parts, list):
                return "/" + "/".join([str(p) for p in path_parts if p is not None])
            if isinstance(path_parts, str):
                return path_parts
            return None

        def walk(o: Any) -> None:
            if isinstance(o, dict):
                if "request" in o and "responseDefinition" in o:
                    req = o.get("request") or {}
                    url = req.get("url") or {}
                    api_path = _as_path(url)
                    method = req.get("method")
                    name = o.get("name")
                    resp_def = o.get("responseDefinition") or {}
                    code = resp_def.get("code")
                    if isinstance(code, int):
                        key = json.dumps(
                            {
                                "api_path": api_path,
                                "method": method,
                                "name": name,
                                "code": code,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        if key not in seen:
                            seen.add(key)
                            codes.append(code)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(col)
        return codes

    @staticmethod
    async def upsert_derived(
        *,
        report_id: str,
        execution_id: str,
        apifox_collection_id: str,
        project_name: str,
        environment: str,
        created_at: datetime,
        report_data: dict,
    ) -> None:
        db = get_mongodb_db()
        summary_col = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]
        failures_col = db[MongoDBReportService.FAILURES_COLLECTION_NAME]
        requests_col = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]

        metrics = MongoDBReportService._extract_metrics(report_data)
        summary = MongoDBReportService._extract_summary(report_data)
        requests_preview = MongoDBReportService._extract_requests(report_data)

        status_buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0, "unknown": 0}
        validation = {"schema_invalid": 0, "code_invalid": 0}
        slow = []
        for r in requests_preview:
            sc = r.get("status_code")
            if sc is None:
                status_buckets["unknown"] += 1
            else:
                try:
                    sc_int = int(sc)
                except Exception:
                    status_buckets["other"] += 1
                else:
                    if 200 <= sc_int <= 299:
                        status_buckets["2xx"] += 1
                    elif 300 <= sc_int <= 399:
                        status_buckets["3xx"] += 1
                    elif 400 <= sc_int <= 499:
                        status_buckets["4xx"] += 1
                    elif 500 <= sc_int <= 599:
                        status_buckets["5xx"] += 1
                    else:
                        status_buckets["other"] += 1
            if r.get("schema_valid") is False:
                validation["schema_invalid"] += 1
            if r.get("code_valid") is False:
                validation["code_invalid"] += 1
            if r.get("latency_ms") is not None:
                slow.append(
                    {
                        "api_path": r.get("api_path"),
                        "method": r.get("method"),
                        "latency_ms": r.get("latency_ms"),
                        "status_code": r.get("status_code"),
                        "name": r.get("name"),
                    }
                )
        slow.sort(key=lambda x: (x.get("latency_ms") or 0), reverse=True)
        run = report_data.get("run") or report_data.get("result") or {}
        total_requests = int((run.get("stats") or {}).get("requests", {}).get("total") or len(requests_preview) or 0)
        if not requests_preview and total_requests > 0:
            expected_codes = MongoDBReportService._extract_expected_status_codes(report_data)
            if expected_codes:
                for code in expected_codes:
                    if 200 <= code <= 299:
                        status_buckets["2xx"] += 1
                    elif 300 <= code <= 399:
                        status_buckets["3xx"] += 1
                    elif 400 <= code <= 499:
                        status_buckets["4xx"] += 1
                    elif 500 <= code <= 599:
                        status_buckets["5xx"] += 1
                    else:
                        status_buckets["other"] += 1
                remain = total_requests - len(expected_codes)
                if remain > 0:
                    status_buckets["unknown"] += remain
            else:
                status_buckets["unknown"] = total_requests
        request_stats = {
            "status_buckets": status_buckets,
            "validation": validation,
            "slow_top": slow[:10],
            "total_requests": total_requests,
        }

        summary_doc = {
            "_id": execution_id,
            "report_id": report_id,
            "execution_id": execution_id,
            "apifox_collection_id": apifox_collection_id,
            "project_name": project_name,
            "environment": environment,
            "created_at": created_at,
            "metrics": metrics,
            "summary": summary,
            "request_stats": request_stats,
            "schema_version": MongoDBReportService.SCHEMA_VERSION,
        }

        await summary_col.update_one(
            {"_id": execution_id},
            {"$set": summary_doc},
            upsert=True,
        )

        failures = MongoDBReportService._extract_failed_cases(report_data)
        failure_docs = []
        for f in failures:
            fp = MongoDBReportService._fingerprint_failure(f)
            failure_docs.append(
                {
                    "_id": f"{execution_id}:{fp}",
                    "report_id": report_id,
                    "execution_id": execution_id,
                    "apifox_collection_id": apifox_collection_id,
                    "project_name": project_name,
                    "environment": environment,
                    "created_at": created_at,
                    "fingerprint": fp,
                    **f,
                    "schema_version": MongoDBReportService.SCHEMA_VERSION,
                }
            )

        if failure_docs:
            for doc in failure_docs:
                await failures_col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

        requests = requests_preview
        if requests:
            for r in requests:
                req_exec_id = r.get("request_exec_id")
                fp = None
                if isinstance(req_exec_id, str) and req_exec_id:
                    fp = req_exec_id
                else:
                    raw = json.dumps(
                        {"api_path": r.get("api_path"), "method": r.get("method"), "name": r.get("name")},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
                doc = {
                    "_id": f"{execution_id}:{fp}",
                    "report_id": report_id,
                    "execution_id": execution_id,
                    "apifox_collection_id": apifox_collection_id,
                    "project_name": project_name,
                    "environment": environment,
                    "created_at": created_at,
                    "schema_version": MongoDBReportService.SCHEMA_VERSION,
                    **r,
                }
                await requests_col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    @staticmethod
    async def ensure_indexes() -> None:
        db = get_mongodb_db()
        raw = db[MongoDBReportService.COLLECTION_NAME]
        summary = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]
        failures = db[MongoDBReportService.FAILURES_COLLECTION_NAME]
        requests = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]
        notes = db[MongoDBReportService.NOTES_COLLECTION_NAME]

        await raw.create_index([("execution_id", 1)], background=True)
        await raw.create_index([("apifox_collection_id", 1), ("created_at", -1)], background=True)

        await summary.create_index([("apifox_collection_id", 1), ("created_at", -1)], background=True)
        await failures.create_index([("apifox_collection_id", 1), ("created_at", -1)], background=True)
        await failures.create_index([("api_path", 1), ("api_method", 1), ("created_at", -1)], background=True)
        await requests.create_index([("apifox_collection_id", 1), ("created_at", -1)], background=True)
        await requests.create_index([("api_path", 1), ("method", 1), ("created_at", -1)], background=True)
        await notes.create_index([("note_type", 1), ("updated_at", -1)], background=True)

    @staticmethod
    async def get_note(*, note_type: str, note_key: str) -> dict | None:
        db = get_mongodb_db()
        notes = db[MongoDBReportService.NOTES_COLLECTION_NAME]
        doc = await notes.find_one({"_id": f"{note_type}:{note_key}"})
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        return None

    @staticmethod
    async def upsert_note(
        *,
        note_type: str,
        note_key: str,
        content: str,
        tags: list[str] | None = None,
        updated_by: str | None = None,
    ) -> dict:
        db = get_mongodb_db()
        notes = db[MongoDBReportService.NOTES_COLLECTION_NAME]
        now = datetime.utcnow()
        doc = {
            "_id": f"{note_type}:{note_key}",
            "note_type": note_type,
            "note_key": note_key,
            "content": content,
            "tags": tags or [],
            "updated_by": updated_by,
            "updated_at": now,
        }
        await notes.update_one({"_id": doc["_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True)
        saved = await notes.find_one({"_id": doc["_id"]})
        if saved:
            saved["_id"] = str(saved["_id"])
            return saved
        return doc
    
    @staticmethod
    async def get_report_by_execution_id(execution_id: str) -> dict | None:
        """根据执行 ID 获取报告"""
        db = get_mongodb_db()
        collection = db[MongoDBReportService.COLLECTION_NAME]
        
        document = await collection.find_one({"execution_id": execution_id})
        if document:
            # 转换 ObjectId 为字符串
            document["_id"] = str(document["_id"])
            return document
        return None
    
    @staticmethod
    async def get_report_by_id(report_id: str) -> dict | None:
        """根据报告 ID 获取报告"""
        db = get_mongodb_db()
        collection = db[MongoDBReportService.COLLECTION_NAME]
        
        try:
            document = await collection.find_one({"_id": ObjectId(report_id)})
            if document:
                document["_id"] = str(document["_id"])
                return document
        except Exception:
            pass
        return None
    
    @staticmethod
    async def delete_report(execution_id: str) -> bool:
        """删除报告"""
        db = get_mongodb_db()
        collection = db[MongoDBReportService.COLLECTION_NAME]
        
        result = await collection.delete_one({"execution_id": execution_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_summary_by_execution_id(execution_id: str) -> dict | None:
        db = get_mongodb_db()
        summary = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]
        doc = await summary.find_one({"_id": execution_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        raw = await MongoDBReportService.get_report_by_execution_id(execution_id)
        if not raw:
            return None
        created_at = raw.get("created_at") or datetime.utcnow()
        report_id = raw.get("_id")
        report_data = raw.get("report") or {}
        metrics = MongoDBReportService._extract_metrics(report_data)
        summary_data = MongoDBReportService._extract_summary(report_data)
        return {
            "_id": execution_id,
            "report_id": report_id,
            "execution_id": execution_id,
            "apifox_collection_id": raw.get("apifox_collection_id", ""),
            "project_name": raw.get("project_name", ""),
            "environment": raw.get("environment", ""),
            "created_at": created_at,
            "metrics": metrics,
            "summary": summary_data,
            "schema_version": MongoDBReportService.SCHEMA_VERSION,
        }

    @staticmethod
    async def get_failure_fingerprints(execution_id: str) -> dict[str, dict]:
        db = get_mongodb_db()
        failures = db[MongoDBReportService.FAILURES_COLLECTION_NAME]
        cursor = failures.find({"execution_id": execution_id})
        rows = await cursor.to_list(length=None)
        if rows:
            out: dict[str, dict] = {}
            for r in rows:
                fp = r.get("fingerprint")
                if fp:
                    out[str(fp)] = r
            return out
        raw = await MongoDBReportService.get_report_by_execution_id(execution_id)
        if not raw:
            return {}
        report_data = raw.get("report") or {}
        failures_raw = MongoDBReportService._extract_failed_cases(report_data)
        out = {}
        for f in failures_raw:
            fp = MongoDBReportService._fingerprint_failure(f)
            out[fp] = f
        return out
    
    # ============ 分析查询方法 ============
    
    @staticmethod
    async def get_trend_analysis(
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 30,
    ) -> list[dict]:
        """
        获取趋势分析数据
        
        Args:
            collection_id: 可选，按集合筛选
            project_id: 可选，按项目筛选
            days: 查询天数
            
        Returns:
            每日统计数据列表
        """
        db = get_mongodb_db()
        summary_collection = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]
        
        # 构建查询条件
        match_stage = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)

        if await summary_collection.count_documents(match_stage, limit=1):
            pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                        },
                        "count": {"$sum": 1},
                        "avg_response_time": {"$avg": "$summary.response_time_avg"},
                        "avg_failed": {"$avg": "$summary.tests_failed"},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            cursor = summary_collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
        
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$metrics.response_time_avg"},
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = raw_collection.aggregate(pipeline)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def get_top_failed_apis(
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 7,
        limit: int = 10,
    ) -> list[dict]:
        """
        获取高频失败 API
        
        Args:
            collection_id: 可选，按集合筛选
            project_id: 可选，按项目筛选
            days: 查询天数
            limit: 返回数量
            
        Returns:
            失败 API 列表
        """
        db = get_mongodb_db()
        failures_collection = db[MongoDBReportService.FAILURES_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]
        
        match_stage = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)

        if await failures_collection.count_documents(match_stage, limit=1):
            pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": {"api_path": "$api_path", "api_method": "$api_method"},
                        "fail_count": {"$sum": 1},
                        "last_fail": {"$max": "$created_at"},
                        "error_messages": {"$addToSet": "$error"},
                        "status_codes": {"$addToSet": "$response_status"},
                    }
                },
                {"$sort": {"fail_count": -1}},
                {"$limit": limit},
            ]
            cursor = failures_collection.aggregate(pipeline)
            return await cursor.to_list(length=None)

        match_stage["failed_cases"] = {"$exists": True, "$ne": []}
        
        pipeline = [
            {"$match": match_stage},
            {"$unwind": "$failed_cases"},
            {
                "$group": {
                    "_id": "$failed_cases.api_path",
                    "fail_count": {"$sum": 1},
                    "last_fail": {"$max": "$created_at"},
                    "error_messages": {"$addToSet": "$failed_cases.error"},
                    "status_codes": {"$addToSet": "$failed_cases.response_status"},
                }
            },
            {"$sort": {"fail_count": -1}},
            {"$limit": limit}
        ]
        
        cursor = raw_collection.aggregate(pipeline)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def get_performance_stats(
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 7,
    ) -> dict:
        """
        获取性能统计
        
        Args:
            collection_id: 可选，按集合筛选
            project_id: 可选，按项目筛选
            days: 查询天数
            
        Returns:
            性能统计数据
        """
        db = get_mongodb_db()
        summary_collection = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]
        
        match_stage = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)

        derived_match = {**match_stage, "summary.response_time_avg": {"$exists": True}}
        if await summary_collection.count_documents(derived_match, limit=1):
            pipeline = [
                {"$match": derived_match},
                {
                    "$group": {
                        "_id": None,
                        "avg_response_time": {"$avg": "$summary.response_time_avg"},
                        "max_response_time": {"$max": "$summary.response_time_max"},
                        "min_response_time": {"$min": "$summary.response_time_min"},
                        "total_executions": {"$sum": 1},
                    }
                },
            ]
            cursor = summary_collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            return result[0] if result else {}

        match_stage["metrics.response_time_avg"] = {"$exists": True}
        
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": None,
                    "avg_response_time": {"$avg": "$metrics.response_time_avg"},
                    "max_response_time": {"$max": "$metrics.response_time_max"},
                    "min_response_time": {"$min": "$metrics.response_time_min"},
                    "total_executions": {"$sum": 1}
                }
            }
        ]
        
        cursor = raw_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return result[0] if result else {}

    @staticmethod
    async def get_overview(
        *,
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 30,
        slow_limit: int = 10,
        signature_limit: int = 10,
    ) -> dict[str, Any]:
        db = get_mongodb_db()
        summary_collection = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]
        failures_collection = db[MongoDBReportService.FAILURES_COLLECTION_NAME]
        requests_collection = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]

        match = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)

        cursor = summary_collection.find(match, projection={"summary": 1, "request_stats": 1})
        docs = await cursor.to_list(length=2000)

        totals = {
            "executions": 0,
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_pending": 0,
        }
        status_buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0, "unknown": 0}
        validation = {"schema_invalid": 0, "code_invalid": 0}
        response_time_sum = 0.0
        response_time_count = 0

        for d in docs:
            totals["executions"] += 1
            s = (d.get("summary") or {})
            totals["tests_total"] += int(s.get("tests_total") or 0)
            totals["tests_passed"] += int(s.get("tests_passed") or 0)
            totals["tests_failed"] += int(s.get("tests_failed") or 0)
            totals["tests_pending"] += int(s.get("tests_pending") or 0)
            rt = s.get("response_time_avg")
            if isinstance(rt, (int, float)):
                response_time_sum += float(rt)
                response_time_count += 1

            rs = (d.get("request_stats") or {})
            buckets = (rs.get("status_buckets") or {})
            for k in status_buckets:
                status_buckets[k] += int(buckets.get(k) or 0)
            v = (rs.get("validation") or {})
            validation["schema_invalid"] += int(v.get("schema_invalid") or 0)
            validation["code_invalid"] += int(v.get("code_invalid") or 0)

        pass_rate = None
        if totals["tests_total"] > 0:
            pass_rate = round(totals["tests_passed"] / totals["tests_total"] * 100, 2)
        avg_response_time = None
        if response_time_count > 0:
            avg_response_time = round(response_time_sum / response_time_count, 2)

        slow_apis: list[dict[str, Any]] = []
        if await requests_collection.count_documents({**match, "latency_ms": {"$ne": None}}, limit=1):
            slow_pipeline = [
                {"$match": {**match, "latency_ms": {"$ne": None}}},
                {
                    "$group": {
                        "_id": {"api_path": "$api_path", "method": "$method"},
                        "avg_latency": {"$avg": "$latency_ms"},
                        "max_latency": {"$max": "$latency_ms"},
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"avg_latency": -1}},
                {"$limit": slow_limit},
            ]
            slow_cursor = requests_collection.aggregate(slow_pipeline)
            slow_apis = await slow_cursor.to_list(length=None)

        top_signatures: list[dict[str, Any]] = []
        if await failures_collection.count_documents(match, limit=1):
            sig_pipeline = [
                {"$match": match},
                {
                    "$group": {
                        "_id": "$signature",
                        "count": {"$sum": 1},
                        "last_seen": {"$max": "$created_at"},
                        "api_path": {"$first": "$api_path"},
                        "api_method": {"$first": "$api_method"},
                        "sample_error": {"$first": "$error"},
                        "error_norm": {"$first": "$error_norm"},
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": signature_limit},
            ]
            sig_cursor = failures_collection.aggregate(sig_pipeline)
            top_signatures = await sig_cursor.to_list(length=None)

        if not docs:
            raw_docs = await raw_collection.find(match, projection={"report": 1}).to_list(length=500)
            for rd in raw_docs:
                report_data = rd.get("report") or {}
                s = MongoDBReportService._extract_summary(report_data)
                totals["executions"] += 1
                totals["tests_total"] += int(s.get("tests_total") or 0)
                totals["tests_passed"] += int(s.get("tests_passed") or 0)
                totals["tests_failed"] += int(s.get("tests_failed") or 0)
                totals["tests_pending"] += int(s.get("tests_pending") or 0)
                rt = s.get("response_time_avg")
                if isinstance(rt, (int, float)):
                    response_time_sum += float(rt)
                    response_time_count += 1

                req_rows = MongoDBReportService._extract_requests(report_data)
                for r in req_rows:
                    sc = r.get("status_code")
                    if sc is None:
                        status_buckets["unknown"] += 1
                    else:
                        try:
                            sc_int = int(sc)
                        except Exception:
                            status_buckets["other"] += 1
                        else:
                            if 200 <= sc_int <= 299:
                                status_buckets["2xx"] += 1
                            elif 300 <= sc_int <= 399:
                                status_buckets["3xx"] += 1
                            elif 400 <= sc_int <= 499:
                                status_buckets["4xx"] += 1
                            elif 500 <= sc_int <= 599:
                                status_buckets["5xx"] += 1
                            else:
                                status_buckets["other"] += 1
                    if r.get("schema_valid") is False:
                        validation["schema_invalid"] += 1
                    if r.get("code_valid") is False:
                        validation["code_invalid"] += 1

                if not slow_apis:
                    buckets: dict[tuple[str | None, str | None], dict[str, Any]] = {}
                    for r in req_rows:
                        lat = r.get("latency_ms")
                        if not isinstance(lat, (int, float)):
                            continue
                        key = (r.get("api_path"), r.get("method"))
                        b = buckets.get(key)
                        if not b:
                            b = {"sum": 0.0, "count": 0, "max": 0.0}
                            buckets[key] = b
                        b["sum"] += float(lat)
                        b["count"] += 1
                        b["max"] = max(b["max"], float(lat))
                    slow_rows = []
                    for (api_path, method), b in buckets.items():
                        avg = b["sum"] / b["count"] if b["count"] else 0
                        slow_rows.append(
                            {
                                "_id": {"api_path": api_path, "method": method},
                                "avg_latency": avg,
                                "max_latency": b["max"],
                                "count": b["count"],
                            }
                        )
                    slow_rows.sort(key=lambda x: x.get("avg_latency", 0), reverse=True)
                    slow_apis = slow_rows[:slow_limit]

                if not top_signatures:
                    sigs: dict[str, dict[str, Any]] = {}
                    for f in MongoDBReportService._extract_failed_cases(report_data):
                        sig = f.get("signature")
                        if not sig:
                            continue
                        cur = sigs.get(sig)
                        if not cur:
                            sigs[sig] = {
                                "_id": sig,
                                "count": 1,
                                "last_seen": datetime.utcnow(),
                                "api_path": f.get("api_path"),
                                "api_method": f.get("api_method"),
                                "sample_error": f.get("error"),
                                "error_norm": f.get("error_norm"),
                            }
                        else:
                            cur["count"] += 1
                    top_signatures = sorted(sigs.values(), key=lambda x: x["count"], reverse=True)[:signature_limit]

            pass_rate = None
            if totals["tests_total"] > 0:
                pass_rate = round(totals["tests_passed"] / totals["tests_total"] * 100, 2)
            avg_response_time = None
            if response_time_count > 0:
                avg_response_time = round(response_time_sum / response_time_count, 2)

        return {
            "totals": totals,
            "pass_rate": pass_rate,
            "avg_response_time": avg_response_time,
            "status_buckets": status_buckets,
            "validation": validation,
            "slow_apis": slow_apis,
            "top_signatures": top_signatures,
        }

    @staticmethod
    async def get_collections(
        *,
        project_id: str | None = None,
        days: int = 365,
    ) -> list[dict[str, Any]]:
        db = get_mongodb_db()
        raw = db[MongoDBReportService.COLLECTION_NAME]
        match = MongoDBReportService._build_match(days=days, collection_id=None, project_id=project_id)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$apifox_collection_id",
                    "count": {"$sum": 1},
                    "last_seen": {"$max": "$created_at"},
                    "project_names": {"$addToSet": "$project_name"},
                }
            },
            {"$sort": {"last_seen": -1}},
        ]
        cursor = raw.aggregate(pipeline)
        return await cursor.to_list(length=None)

    @staticmethod
    async def get_slow_apis(
        *,
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 30,
        limit: int = 10,
        baseline_execution_id: str | None = None,
        target_execution_id: str | None = None,
    ) -> dict[str, Any]:
        db = get_mongodb_db()
        requests_collection = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]
        match = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)

        if baseline_execution_id and target_execution_id:
            left = await MongoDBReportService.get_execution_endpoint_latencies(baseline_execution_id)
            right = await MongoDBReportService.get_execution_endpoint_latencies(target_execution_id)
            keys = set(left.keys()) | set(right.keys())
            rows = []
            for k in keys:
                l = left.get(k)
                r = right.get(k)
                delta = None
                if l is not None and r is not None:
                    delta = r - l
                rows.append(
                    {
                        "api_path": k[0],
                        "method": k[1],
                        "baseline_avg_latency": l,
                        "target_avg_latency": r,
                        "delta": delta,
                    }
                )
            rows.sort(key=lambda x: (x.get("delta") is None, -(x.get("delta") or 0)))
            return {"mode": "compare", "data": rows[:limit]}

        pipeline = [
            {"$match": {**match, "latency_ms": {"$ne": None}}},
            {
                "$group": {
                    "_id": {"api_path": "$api_path", "method": "$method"},
                    "avg_latency": {"$avg": "$latency_ms"},
                    "max_latency": {"$max": "$latency_ms"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"avg_latency": -1}},
            {"$limit": limit},
        ]
        cursor = requests_collection.aggregate(pipeline)
        data = await cursor.to_list(length=None)
        if data:
            return {"mode": "window", "data": data}

        raw_docs = await raw_collection.find(match, projection={"report": 1}).to_list(length=500)
        buckets: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for rd in raw_docs:
            report_data = rd.get("report") or {}
            for r in MongoDBReportService._extract_requests(report_data):
                lat = r.get("latency_ms")
                if not isinstance(lat, (int, float)):
                    continue
                key = (r.get("api_path"), r.get("method"))
                b = buckets.get(key)
                if not b:
                    b = {"sum": 0.0, "count": 0, "max": 0.0}
                    buckets[key] = b
                b["sum"] += float(lat)
                b["count"] += 1
                b["max"] = max(b["max"], float(lat))
        rows = []
        for (api_path, method), b in buckets.items():
            avg = b["sum"] / b["count"] if b["count"] else 0
            rows.append({"_id": {"api_path": api_path, "method": method}, "avg_latency": avg, "max_latency": b["max"], "count": b["count"]})
        rows.sort(key=lambda x: x.get("avg_latency", 0), reverse=True)
        return {"mode": "window", "data": rows[:limit]}

    @staticmethod
    async def get_failure_signatures(
        *,
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        db = get_mongodb_db()
        failures_collection = db[MongoDBReportService.FAILURES_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]
        match = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)
        if not await failures_collection.count_documents(match, limit=1):
            raw_docs = await raw_collection.find(match, projection={"report": 1}).to_list(length=500)
            sigs: dict[str, dict[str, Any]] = {}
            for rd in raw_docs:
                report_data = rd.get("report") or {}
                for f in MongoDBReportService._extract_failed_cases(report_data):
                    sig = f.get("signature")
                    if not sig:
                        continue
                    cur = sigs.get(sig)
                    if not cur:
                        sigs[sig] = {
                            "_id": sig,
                            "count": 1,
                            "last_seen": datetime.utcnow(),
                            "api_path": f.get("api_path"),
                            "api_method": f.get("api_method"),
                            "response_status": f.get("response_status"),
                            "sample_error": f.get("error"),
                            "error_norm": f.get("error_norm"),
                        }
                    else:
                        cur["count"] += 1
            return sorted(sigs.values(), key=lambda x: x["count"], reverse=True)[:limit]
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$signature",
                    "count": {"$sum": 1},
                    "last_seen": {"$max": "$created_at"},
                    "api_path": {"$first": "$api_path"},
                    "api_method": {"$first": "$api_method"},
                    "response_status": {"$first": "$response_status"},
                    "sample_error": {"$first": "$error"},
                    "error_norm": {"$first": "$error_norm"},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        cursor = failures_collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    @staticmethod
    async def get_flaky_endpoints(
        *,
        collection_id: str | None = None,
        project_id: str | None = None,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        db = get_mongodb_db()
        requests_collection = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]
        raw_collection = db[MongoDBReportService.COLLECTION_NAME]
        match = MongoDBReportService._build_match(days=days, collection_id=collection_id, project_id=project_id)

        pipeline = [
            {"$match": match},
            {
                "$addFields": {
                    "is_failed": {
                        "$or": [
                            {"$gte": ["$status_code", 400]},
                            {"$eq": ["$schema_valid", False]},
                            {"$eq": ["$code_valid", False]},
                            {"$eq": ["$passed", False]},
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": {"api_path": "$api_path", "method": "$method"},
                    "total": {"$sum": 1},
                    "failed": {"$sum": {"$cond": ["$is_failed", 1, 0]}},
                    "passed": {"$sum": {"$cond": ["$is_failed", 0, 1]}},
                    "failed_execs": {"$addToSet": {"$cond": ["$is_failed", "$execution_id", "$$REMOVE"]}},
                    "passed_execs": {"$addToSet": {"$cond": ["$is_failed", "$$REMOVE", "$execution_id"]}},
                }
            },
            {
                "$addFields": {
                    "failed_exec_count": {"$size": "$failed_execs"},
                    "passed_exec_count": {"$size": "$passed_execs"},
                }
            },
            {
                "$match": {
                    "failed": {"$gt": 0},
                    "passed": {"$gt": 0},
                    "failed_exec_count": {"$gt": 0},
                    "passed_exec_count": {"$gt": 0},
                }
            },
            {
                "$addFields": {
                    "failure_rate": {
                        "$cond": [{"$gt": ["$total", 0]}, {"$divide": ["$failed", "$total"]}, 0]
                    }
                }
            },
            {"$sort": {"failure_rate": -1, "total": -1}},
            {"$limit": limit},
        ]
        cursor = requests_collection.aggregate(pipeline)
        data = await cursor.to_list(length=None)
        if data:
            return data

        raw_docs = await raw_collection.find(match, projection={"report": 1}).to_list(length=500)
        buckets: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for rd in raw_docs:
            report_data = rd.get("report") or {}
            for r in MongoDBReportService._extract_requests(report_data):
                key = (r.get("api_path"), r.get("method"))
                b = buckets.get(key)
                if not b:
                    b = {"total": 0, "failed": 0}
                    buckets[key] = b
                b["total"] += 1
                is_failed = False
                sc = r.get("status_code")
                if isinstance(sc, (int, float)) and int(sc) >= 400:
                    is_failed = True
                if r.get("schema_valid") is False or r.get("code_valid") is False or r.get("passed") is False:
                    is_failed = True
                if is_failed:
                    b["failed"] += 1
        rows = []
        for (api_path, method), b in buckets.items():
            total = b["total"]
            failed = b["failed"]
            passed = total - failed
            if failed == 0 or passed == 0:
                continue
            rate = failed / total if total else 0
            rows.append({"_id": {"api_path": api_path, "method": method}, "total": total, "failed": failed, "passed": passed, "failure_rate": rate})
        rows.sort(key=lambda x: (x["failure_rate"], x["total"]), reverse=True)
        return rows[:limit]

    @staticmethod
    async def get_execution_endpoint_latencies(execution_id: str) -> dict[tuple[str | None, str | None], float]:
        db = get_mongodb_db()
        requests_collection = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]
        pipeline = [
            {"$match": {"execution_id": execution_id, "latency_ms": {"$ne": None}}},
            {
                "$group": {
                    "_id": {"api_path": "$api_path", "method": "$method"},
                    "avg_latency": {"$avg": "$latency_ms"},
                }
            },
        ]
        cursor = requests_collection.aggregate(pipeline)
        rows = await cursor.to_list(length=None)
        out: dict[tuple[str | None, str | None], float] = {}
        if rows:
            for r in rows:
                key = (r.get("_id", {}).get("api_path"), r.get("_id", {}).get("method"))
                avg = r.get("avg_latency")
                if isinstance(avg, (int, float)):
                    out[key] = float(avg)
            return out

        raw = await MongoDBReportService.get_report_by_execution_id(execution_id)
        if not raw:
            return {}
        report_data = raw.get("report") or {}
        buckets: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for r in MongoDBReportService._extract_requests(report_data):
            lat = r.get("latency_ms")
            if not isinstance(lat, (int, float)):
                continue
            key = (r.get("api_path"), r.get("method"))
            b = buckets.get(key)
            if not b:
                b = {"sum": 0.0, "count": 0}
                buckets[key] = b
            b["sum"] += float(lat)
            b["count"] += 1
        for k, b in buckets.items():
            if b["count"]:
                out[k] = b["sum"] / b["count"]
        return out

    @staticmethod
    async def get_execution_request_profile(execution_id: str) -> dict[str, Any]:
        db = get_mongodb_db()
        requests_collection = db[MongoDBReportService.REQUESTS_COLLECTION_NAME]
        pipeline = [
            {"$match": {"execution_id": execution_id}},
            {
                "$addFields": {
                    "is_failed": {
                        "$or": [
                            {"$gte": ["$status_code", 400]},
                            {"$eq": ["$schema_valid", False]},
                            {"$eq": ["$code_valid", False]},
                            {"$eq": ["$passed", False]},
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": {"api_path": "$api_path", "method": "$method"},
                    "count": {"$sum": 1},
                    "failed": {"$sum": {"$cond": ["$is_failed", 1, 0]}},
                    "avg_latency": {"$avg": "$latency_ms"},
                    "max_latency": {"$max": "$latency_ms"},
                    "min_latency": {"$min": "$latency_ms"},
                }
            },
            {"$sort": {"avg_latency": -1}},
        ]
        cursor = requests_collection.aggregate(pipeline)
        endpoints = await cursor.to_list(length=None)
        if endpoints:
            return {"endpoints": endpoints}

        raw = await MongoDBReportService.get_report_by_execution_id(execution_id)
        if not raw:
            return {"endpoints": []}
        report_data = raw.get("report") or {}
        buckets: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for r in MongoDBReportService._extract_requests(report_data):
            key = (r.get("api_path"), r.get("method"))
            b = buckets.get(key)
            if not b:
                b = {"count": 0, "failed": 0, "sum": 0.0, "max": None, "min": None}
                buckets[key] = b
            b["count"] += 1
            is_failed = False
            sc = r.get("status_code")
            if isinstance(sc, (int, float)) and int(sc) >= 400:
                is_failed = True
            if r.get("schema_valid") is False or r.get("code_valid") is False or r.get("passed") is False:
                is_failed = True
            if is_failed:
                b["failed"] += 1
            lat = r.get("latency_ms")
            if isinstance(lat, (int, float)):
                b["sum"] += float(lat)
                b["max"] = float(lat) if b["max"] is None else max(b["max"], float(lat))
                b["min"] = float(lat) if b["min"] is None else min(b["min"], float(lat))
        rows = []
        for (api_path, method), b in buckets.items():
            avg = b["sum"] / b["count"] if b["count"] else None
            rows.append(
                {
                    "_id": {"api_path": api_path, "method": method},
                    "count": b["count"],
                    "failed": b["failed"],
                    "avg_latency": avg,
                    "max_latency": b["max"],
                    "min_latency": b["min"],
                }
            )
        rows.sort(key=lambda x: (x.get("avg_latency") is None, -(x.get("avg_latency") or 0)))
        return {"endpoints": rows}
