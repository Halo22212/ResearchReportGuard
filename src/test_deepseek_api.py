
import os
from openai import OpenAI

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(
        "没有读取到 API Key。请先在运行配置中设置 DEEPSEEK_API_KEY。"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

print("正在调用 DeepSeek，请稍等……")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "system",
            "content": "你是研报卫士的财务信息提取助手。"
        },
        {
            "role": "user",
            "content": "请提取这句话中的公司、年份、指标和金额："
                       "伊利股份2025年营业收入为1156.36亿元。"
                       "请用中文回答。"
        },
    ],
    stream=False,
)

print("\nDeepSeek 回复：")
print(response.choices[0].message.content)
