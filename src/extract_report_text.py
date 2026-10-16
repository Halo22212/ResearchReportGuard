import os
import fitz  # PyMuPDF

base_dir = os.path.dirname(os.path.abspath(__file__))
reports_dir = os.path.abspath(
    os.path.join(base_dir, "..", "data", "raw", "research_reports")
)

# ---- 1. 看目录里有什么 ----
print("=" * 60)
print(f"扫描目录：{reports_dir}")
print("=" * 60)

if not os.path.isdir(reports_dir):
    print("❌ 目录不存在，请先创建 data/raw/research_reports/")
    raise SystemExit(1)

files = sorted(os.listdir(reports_dir))
print("目录中的文件：")
for f in files:
    full = os.path.join(reports_dir, f)
    size = os.path.getsize(full)
    print(f"  - {f}  ({size:,} 字节)")

# ---- 2. 找 PDF ----
pdfs = [f for f in files if f.lower().endswith(".pdf")]
if not pdfs:
    print("\n❌ 没有找到 PDF 文件。")
    print("如果你只有 .docx，请先在 Word / Pages 里『导出为 PDF』，")
    print("然后把 PDF 放到这个目录里，重新运行本脚本。")
    raise SystemExit(1)

if len(pdfs) > 1:
    print(f"\n⚠️ 发现多个 PDF：{pdfs}")
    print(f"默认使用第一个：{pdfs[0]}")

pdf_name = pdfs[0]
pdf_path = os.path.join(reports_dir, pdf_name)
print(f"\n使用 PDF：{pdf_name}")

# ---- 3. 逐页抽文字 ----
doc = fitz.open(pdf_path)
page_count = doc.page_count          # 先存下来
print(f"PDF 总页数：{page_count}")

all_pages_text = []
total_chars = 0

for i in range(page_count):
    page = doc[i]
    text = page.get_text("text")
    total_chars += len(text.strip())
    all_pages_text.append((i + 1, text))

doc.close()

# ---- 4. 判断是文字版还是扫描版 ----
avg_chars = total_chars / max(page_count, 1)     # 用变量
print(f"总字符数（去空白后估算）：{total_chars}")
print(f"平均每页字符数：{avg_chars:.0f}")

if total_chars < 20:
    print("\n⚠️ 几乎没抽到文字，这可能是扫描版 PDF。")
    print("扫描版需要走 OCR 流程，先确认一下。")
    raise SystemExit(1)
elif avg_chars < 50:
    print("\n⚠️ 每页字符很少，可能是图片为主，或 PDF 结构特殊。")
    print("先把文字存下来看看实际效果。")
else:
    print("\n✅ 看起来是文字版 PDF，抽取成功。")

# ---- 5. 打印预览 ----
print("\n" + "=" * 60)
print("文字预览（每页前 300 字）")
print("=" * 60)
for page_no, text in all_pages_text:
    preview = text.strip().replace("\n", " ")[:300]
    print(f"\n--- 第 {page_no} 页 ---")
    print(preview if preview else "（空）")

# ---- 6. 保存 ----
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "report_text.txt")
)
with open(output_path, "w", encoding="utf-8") as f:
    for page_no, text in all_pages_text:
        f.write(f"========== 第 {page_no} 页 ==========\n")
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
        f.write("\n")

print("\n" + "=" * 60)
print("结果已保存到：")
print(output_path)
print("=" * 60)