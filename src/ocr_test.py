
from pathlib import Path
import shutil
import subprocess
import sys

# 1. 自动定位项目根目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 2. 定位年报首页图片和 OCR 输出文件
image_path = PROJECT_DIR / "outputs" / "pdf_pages" / "page_1.png"
output_path = PROJECT_DIR / "outputs" / "page_1_ocr.txt"

# 3. 检查图片是否存在
if not image_path.exists():
    print(f"错误：找不到图片：{image_path}")
    sys.exit(1)

# 4. 自动查找 Tesseract
tesseract_path = shutil.which("tesseract")

# 如果自动查找失败，尝试 Mac 常见安装位置
if tesseract_path is None:
    possible_paths = [
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]

    for path in possible_paths:
        if Path(path).is_file():
            tesseract_path = path
            break

# 5. 如果还是找不到，给出明确提示
if tesseract_path is None:
    print("错误：Python 没有找到 Tesseract 程序。")
    print("请在 PyCharm Terminal 中运行：")
    print("which tesseract")
    print("然后把输出结果发给我。")
    sys.exit(1)

print(f"找到 Tesseract：{tesseract_path}")
print("正在识别年报首页，请稍等……")

# 6. 执行中文 OCR
try:
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
        check=True,
    )

    # 7. 保存识别结果
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.stdout, encoding="utf-8")

    print("\nOCR 识别成功！")
    print(f"结果保存位置：{output_path}")
    print("\n===== 识别结果预览 =====")
    print(result.stdout[:500])
    print("========================")

except subprocess.CalledProcessError as error:
    print("OCR 执行失败。")
    print("错误信息：")
    print(error.stderr or error.stdout or str(error))
    sys.exit(1)
