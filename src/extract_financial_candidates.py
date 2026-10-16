
from pathlib import Path
import csv
import re

# 1. 定位项目目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 2. 输入和输出文件
input_file = PROJECT_DIR / "outputs" / "annual_report_ocr.txt"
output_file = PROJECT_DIR / "outputs" / "financial_candidates.csv"

if not input_file.exists():
    raise FileNotFoundError(f"找不到 OCR 文件：{input_file}")

# 3. 读取 OCR 全文
text = input_file.read_text(encoding="utf-8")

# 4. 按页码标记拆分年报
page_pattern = re.compile(
    r"={5,}\s*第\s*(\d+)\s*页\s*={5,}"
)

matches = list(page_pattern.finditer(text))

if not matches:
    raise ValueError(
        "没有找到页码标记，请检查 OCR 文件中的分页格式。"
    )

pages = []

for i, match in enumerate(matches):
    start = match.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    page_number = int(match.group(1))
    page_text = text[start:end]
    pages.append((page_number, page_text))

# 5. 设置需要查找的财务指标
keywords = [
    "营业收入",
    "归属于上市公司股东的净利润",
    "归属于母公司股东的净利润",
    "归属于上市公司股东的扣除非经常性损益的净利润",
    "扣除非经常性损益的净利润",
    "经营活动产生的现金流量净额",
]

# 6. 提取附近原文和数字候选
number_pattern = re.compile(
    r"(?<![A-Za-z])[-+]?\d[\d,，]*(?:\.\d+)?%?"
)

rows = []

for page_number, page_text in pages:
    lines = page_text.splitlines()

    for index, line in enumerate(lines):
        for keyword in keywords:
            if keyword not in line:
                continue

            # 保留命中行前后各两行，方便查看表格上下文
            start = max(0, index - 2)
            end = min(len(lines), index + 3)

            context = "\n".join(lines[start:end]).strip()

            numbers = number_pattern.findall(context)

            rows.append({
                "页码": page_number,
                "指标关键词": keyword,
                "候选数字": " | ".join(numbers),
                "原文上下文": context,
                "核验状态": "待人工核验",
            })

# 7. 保存 CSV 文件
output_file.parent.mkdir(parents=True, exist_ok=True)

with output_file.open(
    "w", encoding="utf-8-sig", newline=""
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "页码",
            "指标关键词",
            "候选数字",
            "原文上下文",
            "核验状态",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

print("财务指标候选提取完成！")
print(f"扫描页数：{len(pages)}")
print(f"找到候选记录：{len(rows)}")
print(f"结果文件：{output_file}")

if not rows:
    print("没有找到匹配记录，请检查关键词和 OCR 文字。")
