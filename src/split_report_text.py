import os
import re

base_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "report_text.txt")
)
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "report_sentences_auto.txt")
)

with open(input_path, "r", encoding="utf-8") as f:
    content = f.read()

# ---- 1. 按分页标记拆分 ----
# 匹配 ========== 第 N 页 ==========
page_pattern = re.compile(r"={3,}\s*第\s*(\d+)\s*页\s*={3,}")
parts = page_pattern.split(content)

page_sections = []
for i in range(1, len(parts), 2):
    page_no = int(parts[i])
    page_text = parts[i + 1] if i + 1 < len(parts) else ""
    page_sections.append((page_no, page_text))

print(f"检测到 {len(page_sections)} 页")

# ---- 2. 每页内按中文句末标点切句 ----
sentence_end = re.compile(r"[。！？]")
sentences = []   # [(page_no, sentence), ...]

for page_no, page_text in page_sections:
    # 归一化换行和多余空白
    text = page_text.replace("\n", "").replace("\r", "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        continue

    start = 0
    for m in sentence_end.finditer(text):
        end = m.end()
        sent = text[start:end].strip()
        if sent:
            sentences.append((page_no, sent))
        start = end

    # 处理末尾没有句号的部分（如标题、被截断的句子）
    tail = text[start:].strip()
    if tail:
        sentences.append((page_no, tail))

# ---- 3. 打印 ----
print("=" * 70)
print(f"共切出 {len(sentences)} 句")
print("=" * 70)
for i, (page_no, sent) in enumerate(sentences, 1):
    print(f"{i:2d}. [第 {page_no} 页] {sent}")

# ---- 4. 保存（带页码前缀）----
with open(output_path, "w", encoding="utf-8") as f:
    for page_no, sent in sentences:
        f.write(f"[p{page_no}] {sent}\n")

print()
print("=" * 70)
print(f"结果已保存到：{output_path}")
print("=" * 70)