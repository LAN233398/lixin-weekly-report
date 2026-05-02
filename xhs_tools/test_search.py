import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="/Users/lanyijun/Library/Mobile Documents/com~apple~CloudDocs/lyj+claude/.env")
from firecrawl import V1FirecrawlApp

app = V1FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
result = app.search(query="上海立信会计金融学院", limit=2)
print("类型:", type(result))
print("属性:", [x for x in dir(result) if not x.startswith('_')])
print()
print("数据:", result)
print()
# 尝试获取 data
if hasattr(result, 'data'):
    print("data:", result.data[:2])
