"""
缺陷导入服务

支持多平台缺陷数据导入：
- 解析不同格式文件（JSON、Excel）
- 字段映射转换
- 数据验证
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from io import BytesIO
from typing import Any, BinaryIO

from app.models.defect import (
    DefectCreate,
    DefectSeverity,
    DefectSource,
    ErrorType,
    generate_fingerprint,
)
from app.models.defect_import import (
    DefectImportRecord,
    ImportPlatform,
    ImportStatus,
    ImportPreview,
    ImportResult,
    FieldMappingRule,
    JIRA_FIELD_MAPPING,
    TAPD_FIELD_MAPPING,
    ZENTAO_FIELD_MAPPING,
    EXCEL_FIELD_MAPPING,
    SEVERITY_MAPPING,
    ERROR_TYPE_MAPPING,
)


class ImportParser(ABC):
    """导入解析器基类"""
    
    @abstractmethod
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        """解析文件内容，返回原始数据列表"""
        pass
    
    @abstractmethod
    def get_platform(self) -> str:
        """获取平台类型"""
        pass


class JsonParser(ImportParser):
    """JSON 解析器"""
    
    def get_platform(self) -> str:
        return ImportPlatform.JSON.value
    
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        content = file_content.read()
        data = json.loads(content.decode("utf-8"))
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if "issues" in data:
                return data["issues"]
            elif "data" in data:
                return data["data"]
            elif "defects" in data:
                return data["defects"]
            else:
                return [data]
        else:
            raise ValueError("无法识别的JSON格式")


class JiraParser(JsonParser):
    """Jira 导出解析器"""
    
    def get_platform(self) -> str:
        return ImportPlatform.JIRA.value
    
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        data = super().parse(file_content, file_name)
        
        parsed = []
        for item in data:
            fields = item.get("fields", {})
            parsed.append({
                "id": item.get("id"),
                "key": item.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "priority": fields.get("priority", {}).get("name"),
                "status": fields.get("status", {}).get("name"),
                "issuetype": fields.get("issuetype", {}).get("name"),
                "labels": fields.get("labels", []),
                "components": [c.get("name") for c in fields.get("components", [])],
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "creator": fields.get("creator", {}).get("displayName"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            })
        return parsed


class TapdParser(JsonParser):
    """Tapd 导出解析器"""
    
    def get_platform(self) -> str:
        return ImportPlatform.TAPD.value
    
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        data = super().parse(file_content, file_name)
        
        parsed = []
        for item in data:
            parsed.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "description": item.get("description"),
                "priority": item.get("priority"),
                "severity": item.get("severity"),
                "category": item.get("category"),
                "status": item.get("status"),
                "workitem_type": item.get("workitem_type"),
                "created": item.get("created"),
                "modified": item.get("modified"),
                "creator": item.get("creator"),
                "owner": item.get("owner"),
            })
        return parsed


class ZentaoParser(JsonParser):
    """禅道导出解析器"""
    
    def get_platform(self) -> str:
        return ImportPlatform.ZENTAO.value
    
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        data = super().parse(file_content, file_name)
        
        parsed = []
        for item in data:
            parsed.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "steps": item.get("steps"),
                "severity": item.get("severity"),
                "type": item.get("type"),
                "module": item.get("module"),
                "status": item.get("status"),
                "openedDate": item.get("openedDate"),
                "lastEditedDate": item.get("lastEditedDate"),
                "openedBy": item.get("openedBy"),
                "assignedTo": item.get("assignedTo"),
            })
        return parsed


class ExcelParser(ImportParser):
    """Excel 解析器"""
    
    def get_platform(self) -> str:
        return ImportPlatform.EXCEL.value
    
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("请安装 pandas 和 openpyxl: pip install pandas openpyxl")
        
        df = pd.read_excel(file_content)
        df = df.fillna("")
        
        result = []
        for _, row in df.iterrows():
            item = {}
            for col in df.columns:
                value = row[col]
                if isinstance(value, list):
                    item[col] = value
                elif isinstance(value, str) and value.startswith("["):
                    try:
                        item[col] = json.loads(value)
                    except:
                        item[col] = value
                else:
                    item[col] = str(value) if value else None
            result.append(item)
        
        return result


class CsvParser(ImportParser):
    """CSV 解析器 - 默认使用禅道字段映射"""
    
    def get_platform(self) -> str:
        return ImportPlatform.ZENTAO.value
    
    def parse(self, file_content: BinaryIO, file_name: str) -> list[dict[str, Any]]:
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("请安装 pandas: pip install pandas")
        
        content = file_content.read()
        
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']:
            try:
                decoded = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("无法识别文件编码，请使用 UTF-8 或 GBK 编码")
        
        from io import StringIO
        df = pd.read_csv(StringIO(decoded))
        df = df.fillna("")
        
        result = []
        for _, row in df.iterrows():
            item = {}
            for col in df.columns:
                value = row[col]
                if isinstance(value, list):
                    item[col] = value
                elif isinstance(value, str) and value.startswith("["):
                    try:
                        item[col] = json.loads(value)
                    except:
                        item[col] = value
                else:
                    item[col] = str(value) if value else None
            result.append(item)
        
        return result


PARSER_MAP: dict[str, type[ImportParser]] = {
    ImportPlatform.JSON.value: JsonParser,
    ImportPlatform.JIRA.value: JiraParser,
    ImportPlatform.TAPD.value: TapdParser,
    ImportPlatform.ZENTAO.value: ZentaoParser,
    ImportPlatform.EXCEL.value: ExcelParser,
    "csv": CsvParser,
}


def get_parser(platform: str) -> ImportParser:
    """获取解析器"""
    parser_class = PARSER_MAP.get(platform)
    if not parser_class:
        raise ValueError(f"不支持的平台: {platform}")
    return parser_class()


def detect_platform(file_name: str, content_preview: bytes | None = None) -> str:
    """自动检测平台类型"""
    file_ext = file_name.lower().split(".")[-1]
    
    if file_ext == "csv":
        return "csv"
    
    if file_ext in ("xlsx", "xls"):
        return ImportPlatform.EXCEL.value
    
    if file_ext == "json":
        if content_preview:
            try:
                data = json.loads(content_preview.decode("utf-8"))
                if isinstance(data, dict):
                    if "issues" in data and data.get("expand"):
                        return ImportPlatform.JIRA.value
                    if "workspace_id" in data:
                        return ImportPlatform.TAPD.value
            except:
                pass
        return ImportPlatform.JSON.value
    
    return ImportPlatform.OTHER.value


class FieldMapper:
    """字段映射器 - 支持精确匹配和模糊匹配"""
    
    # 模糊匹配关键词 -> 目标字段
    FUZZY_KEYWORDS: dict[str, list[str]] = {
        "external_id": ["编号", "bug编号", "bugid", "bug_id", "缺陷编号", "工作项id", "缺陷id"],
        "title": ["标题", "bug标题", "缺陷标题", "工作项标题", "名称"],
        "description": ["描述", "重现步骤", "步骤", "复现步骤", "详细描述", "缺陷描述", "bug描述"],
        "severity": ["严重", "优先", "等级", "级别"],
        "error_type": ["类型", "bug类型", "缺陷类型", "错误类型", "工作项类型"],
        "module": ["模块", "组件", "产品", "所属模块", "功能模块"],
        "tags": ["关键词", "标签", "tag", "label", "keyword"],
        "api_path": ["api", "接口", "路径", "url", "path"],
        "api_method": ["方法", "method", "请求方法"],
    }
    
    def __init__(self, platform: str, custom_mapping: dict[str, str] | None = None):
        self.platform = platform
        self.custom_mapping = custom_mapping or {}
        
        default_mappings = {
            ImportPlatform.JIRA.value: JIRA_FIELD_MAPPING,
            ImportPlatform.TAPD.value: TAPD_FIELD_MAPPING,
            ImportPlatform.ZENTAO.value: ZENTAO_FIELD_MAPPING,
            ImportPlatform.EXCEL.value: EXCEL_FIELD_MAPPING,
            ImportPlatform.JSON.value: {},
            "csv": ZENTAO_FIELD_MAPPING,
        }
        self.default_mapping = default_mappings.get(platform, ZENTAO_FIELD_MAPPING)
    
    def _fuzzy_match(self, field_name: str) -> str | None:
        """模糊匹配字段名"""
        name_lower = field_name.lower().strip()
        for target, keywords in self.FUZZY_KEYWORDS.items():
            for kw in keywords:
                if kw in name_lower or name_lower in kw:
                    return target
        return None
    
    def map_field(self, source_field: str, source_value: Any) -> tuple[str, Any]:
        """映射单个字段：先精确匹配，再模糊匹配"""
        # 去除字段名中的空格，处理禅道CSV中可能存在的空格问题
        source_field_clean = source_field.strip()
        
        target_field = (
            self.custom_mapping.get(source_field_clean)
            or self.custom_mapping.get(source_field)
            or self.default_mapping.get(source_field_clean)
            or self.default_mapping.get(source_field)
            or self._fuzzy_match(source_field_clean)
        )
        
        if not target_field:
            return source_field, source_value
        
        target_value = self.transform_value(target_field, source_value)
        return target_field, target_value
    
    def transform_value(self, target_field: str, source_value: Any) -> Any:
        """转换字段值"""
        if target_field == "severity":
            if isinstance(source_value, str):
                v = source_value.strip()
                return SEVERITY_MAPPING.get(v, SEVERITY_MAPPING.get(v.lower(), DefectSeverity.NORMAL.value))
            elif isinstance(source_value, (int, float)):
                return SEVERITY_MAPPING.get(str(int(source_value)), DefectSeverity.NORMAL.value)
            return DefectSeverity.NORMAL.value
        
        if target_field == "error_type":
            if isinstance(source_value, str):
                v = source_value.strip()
                return ERROR_TYPE_MAPPING.get(v, ERROR_TYPE_MAPPING.get(v.lower(), ErrorType.OTHER.value))
            return ErrorType.OTHER.value
        
        if target_field == "tags":
            if isinstance(source_value, str):
                if source_value.startswith("["):
                    try:
                        return json.loads(source_value)
                    except Exception:
                        return [source_value]
                return [t.strip() for t in source_value.replace("，", ",").replace(";", ",").replace("；", ",").split(",") if t.strip()]
            elif isinstance(source_value, list):
                return source_value
            return []
        
        return source_value
    
    def map_record(self, source_record: dict[str, Any]) -> dict[str, Any]:
        """映射整条记录"""
        result = {}
        for source_field, source_value in source_record.items():
            if source_value is None or source_value == "":
                continue
            target_field, target_value = self.map_field(source_field, source_value)
            # 只有当目标字段不同于源字段，或者结果中还没有该字段时才设置
            if target_field not in result or target_field != source_field:
                result[target_field] = target_value
        return result


class DefectImportService:
    """缺陷导入服务"""
    
    @staticmethod
    def parse_file(
        file_content: BinaryIO,
        file_name: str,
        platform: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        解析导入文件
        
        Returns:
            (平台类型, 原始数据列表)
        """
        if not platform:
            content_preview = file_content.read(1024)
            file_content.seek(0)
            platform = detect_platform(file_name, content_preview)
        
        parser = get_parser(platform)
        data = parser.parse(file_content, file_name)
        
        return platform, data
    
    @staticmethod
    def preview_import(
        raw_data: list[dict[str, Any]],
        platform: str,
        field_mapping: dict[str, str] | None = None,
    ) -> ImportPreview:
        """
        预览导入数据
        
        Returns:
            ImportPreview
        """
        mapper = FieldMapper(platform, field_mapping)
        
        preview_data = []
        errors = []
        new_count = 0
        duplicate_count = 0
        
        for idx, record in enumerate(raw_data):
            try:
                mapped = mapper.map_record(record)
                
                if idx < 3:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"=== 记录 {idx} ===")
                    logger.info(f"原始字段: {list(record.keys())}")
                    logger.info(f"原始数据: {record}")
                    logger.info(f"映射后: {mapped}")
                    logger.info(f"提取: title={mapped.get('title')}, source_id={mapped.get('source_id')}, severity={mapped.get('severity')}, module={mapped.get('module')}, error_type={mapped.get('error_type')}")
                
                title = mapped.get("title") or mapped.get("summary") or f"导入记录 {idx + 1}"
                
                severity = mapped.get("severity", DefectSeverity.NORMAL.value)
                if isinstance(severity, str):
                    severity = SEVERITY_MAPPING.get(severity.strip(), SEVERITY_MAPPING.get(severity.lower(), DefectSeverity.NORMAL.value))
                if isinstance(severity, int):
                    severity = SEVERITY_MAPPING.get(str(severity), DefectSeverity.NORMAL.value)
                
                tags = mapped.get("tags")
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.replace("，", ",").split(",") if t.strip()]
                elif tags is None:
                    tags = []
                
                description = mapped.get("description", "")
                if description and len(str(description)) > 5000:
                    description = str(description)[:5000] + "..."
                
                # 获取外部ID (Bug编号)
                external_id = mapped.get("external_id") or mapped.get("source_id", "")
                
                defect_create = DefectCreate(
                    title=str(title)[:200],
                    description=str(description) if description else None,
                    source=DefectSource.IMPORT.value,
                    source_id=str(external_id)[:100] if external_id else None,
                    api_path=mapped.get("api_path"),
                    api_method=mapped.get("api_method"),
                    module=mapped.get("module"),
                    error_type=mapped.get("error_type"),
                    severity=severity,
                    tags=tags,
                )
                
                if defect_create.api_path:
                    defect_create.fingerprint = generate_fingerprint(
                        api_path=defect_create.api_path,
                        api_method=defect_create.api_method,
                        error_type=defect_create.error_type,
                        error_message=defect_create.description,
                    )
                
                preview_data.append({
                    "index": idx,
                    "external_id": defect_create.source_id or "",
                    "title": defect_create.title,
                    "description": (str(defect_create.description)[:100] + "...") if defect_create.description and len(str(defect_create.description)) > 100 else (defect_create.description or ""),
                    "severity": defect_create.severity,
                    "error_type": defect_create.error_type or "",
                    "module": defect_create.module or "",
                    "tags": defect_create.tags or [],
                    "api_path": defect_create.api_path,
                    "defect_create": defect_create.model_dump(),
                })
                
            except Exception as e:
                errors.append({
                    "index": idx,
                    "raw_data": record,
                    "error": str(e),
                })
        
        return ImportPreview(
            total_count=len(raw_data),
            new_count=len(preview_data),
            duplicate_count=0,
            error_count=len(errors),
            preview_data=preview_data[:20],
            field_mapping=mapper.default_mapping,
            errors=errors[:10],
        )
    
    @staticmethod
    def convert_to_defect_create(
        mapped_data: dict[str, Any],
    ) -> DefectCreate:
        """将映射后的数据转换为 DefectCreate"""
        title = mapped_data.get("title") or mapped_data.get("summary") or "未命名缺陷"
        
        return DefectCreate(
            title=str(title)[:200],
            description=mapped_data.get("description"),
            source=DefectSource.IMPORT.value,
            api_path=mapped_data.get("api_path"),
            api_method=mapped_data.get("api_method"),
            module=mapped_data.get("module"),
            error_type=mapped_data.get("error_type"),
            severity=mapped_data.get("severity", DefectSeverity.NORMAL.value),
            tags=mapped_data.get("tags"),
        )
