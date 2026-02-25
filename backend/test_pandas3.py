import pandas as pd
from io import StringIO

csv_content = """"Bug编号","所属产品","所属模块","所属项目","Bug标题","严重程度","优先级","Bug类型","重现步骤","指派给","指派日期"
"1	","测试辅助平台(#1)","/(#0)","0	","使用正确的用户名和密码登录","1(#1)","1(#1)","代码错误(#codeerror)","[前置条件] 用户提前完成注册[步骤]2. 输入正确的密码[结果]2. 密码明文显示了[期望]2. 密码加密显示","","",""
"""

# 打印每一行的列数
lines = csv_content.strip().split('
')
for i, line in enumerate(lines):
    # 简单的按逗号分割（不考虑引号内的逗号）
    cols = line.split('","')
    print(f"Line {i+1} has {len(cols)} columns")

# 使用 pandas 读取，忽略多余的列
df = pd.read_csv(StringIO(csv_content), on_bad_lines='skip')
print(df.to_dict('records'))

# 尝试手动修复数据行
fixed_lines = [lines[0]]
for line in lines[1:]:
    # 移除最后一个多余的空字符串
    if line.endswith(',""'):
        line = line[:-3]
    fixed_lines.append(line)

fixed_csv_content = '
'.join(fixed_lines)
print("
--- Fixed CSV ---")
df_fixed = pd.read_csv(StringIO(fixed_csv_content))
print(df_fixed.to_dict('records'))
