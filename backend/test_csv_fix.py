import json
from io import BytesIO
from app.services.defect_import import DefectImportService, CsvParser, FieldMapper

# 使用用户提供的 CSV 文件内容
csv_content = """"Bug 编号","所属产品","所属模块","所属项目","Bug 标题","严重程度","优先级","Bug 类型","重现步骤","指派给","指派日期"
"1	","测试辅助平台 (#1)","/(#0)","0	","使用正确的用户名和密码登录","1(#1)","1(#1)","代码错误 (#codeerror)","[前置条件] 用户提前完成注册 [步骤]2. 输入正确的密码 [结果]2. 密码明文显示了 [期望]2. 密码加密显示","","",""
"""

print("=== 测试 CSV 解析 ===")
parser = CsvParser()
raw_data = parser.parse(BytesIO(csv_content.encode('utf-8')), "test.csv")
print("Raw data:", json.dumps(raw_data, ensure_ascii=False, indent=2))

print("\n=== 测试字段映射 ===")
mapper = FieldMapper("csv")
for record in raw_data:
    mapped = mapper.map_record(record)
    print("Mapped:", json.dumps(mapped, ensure_ascii=False, indent=2))

print("\n=== 测试预览导入 ===")
preview = DefectImportService.preview_import(raw_data, "csv")
print("Preview:", json.dumps(preview.model_dump(), ensure_ascii=False, indent=2))