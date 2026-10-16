import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

# ---- 1. 初始化 ----
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("没有读取到 API Key，请检查项目根目录下的 .env 文件")

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

base_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "report_text.txt")
)
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "extracted_claims_from_report.json")
)

# ---- 2. 读文件，按页拆分 ----
with open(input_path, "r", encoding="utf-8") as f:
    report_content = f.read()

page_pattern = re.compile(r"={3,}\s*第\s*(\d+)\s*页\s*={3,}")
parts = page_pattern.split(report_content)

pages = []   # [(page_no, text), ...]
for i in range(1, len(parts), 2):
    page_no = int(parts[i])
    text = parts[i + 1] if i + 1 < len(parts) else ""
    pages.append((page_no, text))

print(f"检测到 {len(pages)} 页")

# ---- 3. 提示词 ----
system_prompt = """你是金融研究报告的财务信息抽取助手。

请从用户提供的研报页面文字中，提取所有可以核查的财务陈述。

【核心任务】
一页文字可能包含：标题、正文、表格、脚注。请识别出所有"具体数字 + 财务指标"的陈述。

【三个关键判断】
1. 主语补全
   - 如果陈述省略了公司主语（如只说"公司实现营收..."），
     请从标题或上下文推断公司名，填入 company。
   - 无法推断时，company 填 null。

2. 预测性判断
   - 如果陈述是对"未来"的预测（出现"预计""有望""将达到""目标价""我们预测"等），
     标记 is_forecast = true。这类陈述不属于"已发生事实"，不应核查。
   - 如果是对"已发生"事实的陈述（如"2025年营收XX亿"），标记 is_forecast = false。

3. 一条陈述一条记录
   - 不要合并不同指标；不要拆分同一陈述。
   - 标题里的"XX公司（代码）"不算独立陈述，除非含具体财务数字。

【严格返回 JSON】
{
  "claims": [
    {
      "company": "伊利股份",
      "metric": "营业收入",
      "year": 2025,
      "amount": 1156.36,
      "unit": "亿元",
      "yoy_percent": 0.21,
      "is_forecast": false,
      "source_text": "公司2025 年实现营业收入1156.36 亿元，同比增长0.21%。",
      "uncertainties": []
    }
  ]
}

字段约定：
- company、metric、unit、source_text 用字符串；无法确定用 null
- year 用整数；无法确定用 null
- amount、yoy_percent 用数字；无法确定用 null
- yoy_percent 用"百分点"形式：0.21 表示 0.21%；下降写成负数（如 -34.02）
- is_forecast 用布尔值
- uncertainties 用字符串数组，记录歧义（如"主语不明确"、"单位缺失"），无歧义时为空数组

【输出约束】
- 只输出 JSON 对象，不要 Markdown 代码块，不要任何其他文字。
- 如果这一页没有任何可核查的陈述，返回 {"claims": []}。
"""

# ---- 4. 逐页送模型 ----
all_claims = []

for page_no, page_text in pages:
    page_text = page_text.strip()
    if not page_text:
        print(f"--- 第 {page_no} 页（空）跳过 ---")
        continue

    print(f"\n{'=' * 70}")
    print(f"处理第 {page_no} 页（{len(page_text)} 字符）")
    print(f"{'=' * 70}")

    user_msg = f"以下是研报第 {page_no} 页的全部文字：\n\n{page_text}"

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content

    try:
        parsed = json.loads(raw)
        claims = parsed.get("claims", [])
        # 强制填 page 字段（不信任模型自己填）
        for c in claims:
            c["page"] = page_no
        all_claims.extend(claims)
        print(f"模型返回 {len(claims)} 条主张：")
        for c in claims:
            fc = "🔮预测" if c.get("is_forecast") else "✅事实"
            print(f"  [{fc}] {c.get('metric')} {c.get('amount')} {c.get('unit')} "
                  f"(yoy {c.get('yoy_percent')}%) - 公司: {c.get('company')}")
    except json.JSONDecodeError as e:
        print("⚠️ JSON 解析失败：", e)
        print("原始返回：", raw[:500])

# ---- 5. 保存 ----
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({"claims": all_claims}, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 70}")
print(f"共提取 {len(all_claims)} 条主张")
print(f"结果已保存到：{output_path}")
print(f"{'=' * 70}")