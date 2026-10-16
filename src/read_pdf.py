
from pathlib import Path
import fitz

# 项目根目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# PDF 文件位置
pdf_path = PROJECT_DIR / "data" / "raw" / "annual_report.pdf"

# 图片输出目录
output_dir = PROJECT_DIR / "outputs" / "pdf_pages"
output_dir.mkdir(parents=True, exist_ok=True)

# 检查 PDF 是否存在
if not pdf_path.exists():
    raise FileNotFoundError(f"找不到 PDF 文件：{pdf_path}")

# 打开 PDF
doc = fitz.open(pdf_path)

print(f"PDF 总页数：{len(doc)}")
print("开始转换，请稍等……")

# 每一页都转换成 PNG 图片
for page_index, page in enumerate(doc):
    pix = page.get_pixmap(
        matrix=fitz.Matrix(1.5, 1.5),
        alpha=False
    )

    image_path = output_dir / f"page_{page_index + 1}.png"
    pix.save(image_path)

    # 每完成 20 页显示一次进度
    if (page_index + 1) % 20 == 0 or page_index + 1 == len(doc):
        print(f"已完成：{page_index + 1}/{len(doc)} 页")

doc.close()

print("全部转换完成！")
print(f"图片保存目录：{output_dir}")
