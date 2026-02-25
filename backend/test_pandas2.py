import pandas as pd
from io import StringIO

csv_content = """"Bug编号","所属产品","所属模块","所属项目","Bug标题","严重程度","优先级","Bug类型","重现步骤","指派给","指派日期"
"1	","测试辅助平台(#1)","/(#0)","0	","使用正确的用户名和密码登录","1(#1)","1(#1)","代码错误(#codeerror)","[前置条件] 用户提前完成注册[步骤]2. 输入正确的密码[结果]2. 密码明文显示了[期望]2. 密码加密显示","","",""
"""

print("--- Using default comma separator ---")
df1 = pd.read_csv(StringIO(csv_content))
print(df1.to_dict('records'))

print("\n--- Using tab separator ---")
try:
    df2 = pd.read_csv(StringIO(csv_content), sep='\t')
    print(df2.to_dict('records'))
except Exception as e:
    print("Error:", e)

print("\n--- Using comma separator with skipinitialspace ---")
df3 = pd.read_csv(StringIO(csv_content), skipinitialspace=True)
print(df3.to_dict('records'))

print("\n--- Using comma separator and stripping whitespace from columns and values ---")
df4 = pd.read_csv(StringIO(csv_content))
df4.columns = df4.columns.str.strip()
for col in df4.columns:
    if df4[col].dtype == 'object':
        df4[col] = df4[col].str.strip()
print(df4.to_dict('records'))
