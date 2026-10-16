
from pathlib import Path
import re
import csv
from decimal import Decimal, InvalidOperation

PROJECT_DIR = Path(__file__).resolve().parent.parent
OCR_FILE = PROJECT_DIR / "outputs" / "annual_report_ocr.txt"
OUTPUT_FILE = PROJECT_DIR / "outputs" / "financial_verification.csv"

STANDARD_DATA = {
    "营业收入_2025": {
        "year": "2025",
        "amount": "115636231250.05",
    },
    "营业收入_2024": {
        "year": "2024",
        "amount": "115393310976.69",
    },
}


def normalize_number(raw):
    """清理 OCR 金额中的空格、千位分隔符和小数点。"""
    value = raw.strip()
    value = value.replace(",", "").replace("，", "")
    value = value.replace(" ", "").replace("。", ".")
    value = re.sub(r"[^0-9.]", "", value)

    if not value or value.count(".") > 1:
        return None

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def split_pages(text):
    """按照 OCR 文件中的页码标记拆分页面。"""
    pattern = re.compile(r"={5,}\s*第\s*(\d+)\s*页\s*={5,}")
    matches = list(pattern.finditer(text))
    pages = []

    for i, match in enumerate(matches):
        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        pages.append({
            "page": int(match.group(1)),
            "text": text[start:end],
        })

    return pages


def find_amount_context(page_text, target):
    """在单页中查找目标金额，并返回原文上下文。"""

    number_pattern = re.compile(
        r"\d{1,3}(?:\s*[,，]\s*\d{3})+"
        r"(?:\s*[.。]\s*\d{1,2})?"
        r"|\d+(?:\s*[.。]\s*\d{1,2})?"
    )

    for match in number_pattern.finditer(page_text):
        raw = match.group()
        normalized = normalize_number(raw)

        if normalized == target:
            start = max(0, match.start() - 250)
            end = min(len(page_text), match.end() + 250)
            context = page_text[start:end].replace("\n", " ")
            return raw, context

    return None, None


def page_priority(page_text):
    """优先检查包含主要会计数据和营业收入的页面。"""
    score = 0

    if "主要会计数据" in page_text:
        score += 5

    if "营业收入" in page_text:
        score += 5

    if "2025年" in page_text or "2025 年" in page_text:
        score += 2

    if "2024年" in page_text or "2024 年" in page_text:
        score += 2

    return score


def verify_one(name, info, pages):
    """核验一个指标，优先搜索相关页面。"""
    year = info["year"]
    target = Decimal(info["amount"])

    ranked_pages = sorted(
        pages,
        key=lambda page: page_priority(page["text"]),
        reverse=True,
    )

    # 第一轮：优先检查主要会计数据等相关页面。
    # 第二轮：再检查其他页面，避免漏掉金额。
    for page in ranked_pages:
        page_text = page["text"]
        raw, context = find_amount_context(page_text, target)

        if raw is None:
            continue

        # 判断年份和指标是否出现在同一页及金额附近。
        year_in_context = year in context
        indicator_in_context = "营业收入" in context

        # 如果附近没有年份或指标，但整页有相关关键词，
        # 记录下来供人工核查，不直接判为通过。
        year_in_page = (
            year in page_text
            or f"{year} 年" in page_text
        )
        indicator_in_page = "营业收入" in page_text

        if year_in_context and indicator_in_context:
            status = "金额、年份和指标关键词均出现，仍需人工确认"
        elif year_in_page and indicator_in_page:
            status = "同页找到金额、年份和指标，需人工确认表格对应关系"
        else:
            status = "找到相同金额，但年份或指标证据不足"

        return {
            "指标": name,
            "标准金额（元）": info["amount"],
            "OCR中找到金额": "是",
            "年报PDF页码": page["page"],
            "OCR原始金额": raw,
            "上下文含目标年份": "是" if year_in_context else "否",
            "页面含目标年份": "是" if year_in_page else "否",
            "上下文含营业收入": (
                "是" if indicator_in_context else "否"
            ),
            "页面含营业收入": (
                "是" if indicator_in_page else "否"
            ),
            "核验状态": status,
            "年报原文证据": context,
        }

    return {
        "指标": name,
        "标准金额（元）": info["amount"],
        "OCR中找到金额": "否",
        "年报PDF页码": "",
        "OCR原始金额": "",
        "上下文含目标年份": "否",
        "页面含目标年份": "否",
        "上下文含营业收入": "否",
        "页面含营业收入": "否",
        "核验状态": "未找到对应金额，需检查 OCR",
        "年报原文证据": "",
    }


def main():
    if not OCR_FILE.exists():
        raise FileNotFoundError(f"找不到 OCR 文件：{OCR_FILE}")

    text = OCR_FILE.read_text(encoding="utf-8")
    pages = split_pages(text)

    if not pages:
        raise ValueError(
            "没有识别到页码标记，请检查 annual_report_ocr.txt。"
        )

    rows = []

    for name, info in STANDARD_DATA.items():
        rows.append(verify_one(name, info, pages))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "指标",
        "标准金额（元）",
        "OCR中找到金额",
        "年报PDF页码",
        "OCR原始金额",
        "上下文含目标年份",
        "页面含目标年份",
        "上下文含营业收入",
        "页面含营业收入",
        "核验状态",
        "年报原文证据",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("财务数据核验完成！")

    for row in rows:
        print(
            f"{row['指标']}: {row['核验状态']} "
            f"| PDF页码：{row['年报PDF页码'] or '未找到'}"
        )

    print(f"结果已保存到：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
