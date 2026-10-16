
from pathlib import Path
import shutil
import subprocess
import sys

# 项目根目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 图片目录和输出文件
image_dir = PROJECT_DIR / "outputs" / "pdf_pages"
output_file = PROJECT_DIR / "outputs" / "annual_report_ocr.txt"

# 查找 Tesseract
tesseract_path = shutil.which("tesseract")

if tesseract_path is None:
    for path in [
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]:
        if Path(path).is_file():
            tesseract_path = path
            break

if tesseract_path is None:
    raise FileNotFoundError(
        "找不到 Tesseract，请检查 OCR 环境。"
    )

# 找到所有页面图片，并按页码排序
images = list(image_dir.glob("page_*.png"))
images.sort(key=lambda p: int(p.stem.split("_")[1]))

if not images:
    raise FileNotFoundError(f"没有找到页面图片：{image_dir}")

print(f"共找到 {len(images)} 张图片")
print("开始批量 OCR，请耐心等待……")

output_file.parent.mkdir(parents=True, exist_ok=True)

# 逐页识别，避免一次占用过多内存
with output_file.open("w", encoding="utf-8") as f:
    for index, image_path in enumerate(images, start=1):
        result = subprocess.run(
            [
                tesseract_path,
                str(image_path),
                "stdout",
                "-l",
                "chi_sim",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            print(f"第 {index} 页识别失败：{result.stderr}")
            continue

        f.write(f"\n\n========== 第 {index} 页 ==========\n\n")
        f.write(result.stdout)

        if index % 10 == 0 or index == len(images):
            print(f"进度：{index}/{len(images)} 页")

print("\n批量 OCR 完成！")
print(f"文字文件：{output_file}")
