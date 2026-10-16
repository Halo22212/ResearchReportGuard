import os
import fitz  # PyMuPDF

base_dir = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.abspath(
    os.path.join(base_dir, "..", "data", "raw", "annual_report.pdf")
)
out_dir = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "evidence")
)
os.makedirs(out_dir, exist_ok=True)

# OCR 里的"第 7 页"→ PyMuPDF 的 page index = 6（从 0 计数）
PAGE_INDEX = 6

doc = fitz.open(pdf_path)
print("PDF 总页数：", doc.page_count)

page = doc[PAGE_INDEX]

# ---- 1. 整页高分辨率渲染（约 288 dpi）----
zoom = 4.0
mat = fitz.Matrix(zoom, zoom)
pix = page.get_pixmap(matrix=mat, alpha=False)
full_path = os.path.join(out_dir, "page_7_full.png")
pix.save(full_path)
print("整页图像：", full_path)
print("  尺寸：", pix.width, "x", pix.height)

# ---- 2. 裁出"主要会计数据"表格区域（页面上半部分，先粗裁）----
clip = fitz.Rect(
    page.rect.x0,
    page.rect.y0 + page.rect.height * 0.05,
    page.rect.x1,
    page.rect.y0 + page.rect.height * 0.55,
)
pix2 = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
table_path = os.path.join(out_dir, "page_7_table.png")
pix2.save(table_path)
print("表格区域图像：", table_path)
print("  尺寸：", pix2.width, "x", pix2.height)

doc.close()
print("\n完成。请在 PyCharm 项目树里双击打开这两个 PNG 看一下。")