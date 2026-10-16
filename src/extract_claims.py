import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# 1. 读取 API Key
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("没有读取到 API Key，请检查项目根目录下的 .env 文件")

# 2. 连接 DeepSeek
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# 3. 从外部文件读取待核查句子
base_dir = os.path.dirname(os.path.abspath(__file__))
input_txt = os.path.abspath(
    os.path.join(base_dir, "..", "data", "inputs", "report_sentences.txt")
)

if not os.path.exists(input_txt):
    raise FileNotFoundError(f"找不到输入文件：{input_txt}")

with open(input_txt, "r", encoding="utf-8") as f:
    lines = f.readlines()

report_texts = []
for line in lines:
    s = line.strip()
    if not s:                # 跳过空行
        continue
    if s.startswith("#"):    # 跳过注释行
        continue
    report_texts.append(s)

print(f"从文件读到 {len(report_texts)} 句待核查文本")
print(f"文件路径：{input_txt}\n")

# 4. 抽取提示词
system_prompt = """你是金融研究报告的信息抽取助手。
请从用户提供的研报文字中提取明确出现的财务陈述。
只能提取原文信息，不得猜测、补充或自行计算。

请严格返回一个 JSON 对象，格式如下：
{
  "claims": [
    {
      "company": "公司名称",
      "metric": "财务指标名称",
      "year": 2025,
      "amount": 1156.36,
      "unit": "亿元",
      "yoy_percent": 0.21,
      "source_text": "原文中的完整陈述",
      "uncertainties": []
    }
  ]
}

要求：
1. company、metric、unit、source_text 使用字符串。
2. year 使用整数；无法确定时填写 null。
3. amount 和 yoy_percent 使用数字；原文没有明确给出时填写 null。
4. yoy_percent 使用"百分点"形式：0.21 表示 0.21%；如果原文是"下降 34.02%"，必须写成 -34.02。
5. uncertainties 使用字符串数组，记录存在的歧义；没有则返回空数组。
6. 不要输出 Markdown 代码块，不要输出 JSON 以外的解释。
"""

# 5. 逐句调用
all_claims = []
for idx, text in enumerate(report_texts, start=1):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content
    print(f"--- 第 {idx} 句 ---")
    print("输入：", text)
    print("返回：", raw)
    try:
        parsed = json.loads(raw)
        all_claims.extend(parsed.get("claims", []))
    except json.JSONDecodeError as e:
        print("⚠️ JSON 解析失败：", e)

# 6. 保存
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "extracted_claims.json")
)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"claims": all_claims}, f, ensure_ascii=False, indent=2)

print(f"\n共提取 {len(all_claims)} 条主张")
print("结果已保存到：", output_path)