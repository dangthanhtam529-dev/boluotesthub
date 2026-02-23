import sys
data = open(r'backend\app\services\apifox.py', 'rb').read()
text = data.decode('utf-8', 'replace')
with open('_apifox_dump.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print('wrote ' + str(len(text)) + ' chars to _apifox_dump.txt')
