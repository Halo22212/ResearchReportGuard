
from pathlib import Path
import csv
from decimal import Decimal

PROJECT_DIR = Path(__file__).resolve().parent.parent

VERIFICATION_FILE = (
    PROJECT_DIR / "outputs" / "financial_verification.csv"
)

OUTPUT_FILE = PROJECT_DIR / "outputs" / "claim_check_results.csv"


# 模拟研报中提取出来的财务说法。
# 目前先手动填写，下一阶段再接入 DeepSeek 自动提取。
TEST_CLAIMS = [
    {
        "编号": "测试001",
        "研报说法": "2025年营业收入为1156.36亿元",
        "指标": "营业收入",
        "年份": "2025",
        "金额_元": "115636231250.05",
    },
    {
        "编号": "测试002",
        "研报说法": "2025年营业收入为1200亿元",
        "指标": "营业收入",
        "年份": "2025",
        "金额_元": "120000000000",
    },
    {
        "编号": "测试003",
        "研报说法": "2024年营业收入为1156.36亿元",
        "指标": "营业收入",
        "年份": "2024",
        "金额_元": "115636231250.05",
    },
]


# 标准数据来自我们目前整理的年报数据。
# 后续应继续核对原始年报，扩充更多指标。
STANDARD_DATA = {
    ("营业收入", "2025"): "115636231250.05",
    ("营业收入", "2024"): "115393310976.69",
}


def load_evidence():
    """读取前一步生成的年报核验结果。"""
    if not VERIFICATION_FILE.exists():
        raise FileNotFoundError(
            "找不到财务核验结果，请先运行 verify_financial_data.py"
        )

    with VERIFICATION_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        return list(csv.DictReader(f))


def find_evidence(indicator, year, evidence_rows):
    """查找对应年份和指标的年报证据。"""
    key = f"{indicator}_{year}"

    for row in evidence_rows:
        if row.get("指标") == key:
            return row

    return None


def check_claim(claim, evidence_rows):
    """比较研报说法与标准金额，并附上证据定位。"""
    indicator = claim["指标"]
    year = claim["年份"]
    claimed_amount = Decimal(claim["金额_元"])

    standard_text = STANDARD_DATA.get((indicator, year))
    evidence = find_evidence(indicator, year, evidence_rows)

    if standard_text is None:
        status = "待核查：暂无对应标准数据"
        standard_amount = ""
    else:
        standard_amount = standard_text
        standard_amount_decimal = Decimal(standard_text)

        if claimed_amount == standard_amount_decimal:
            status = "金额一致：仍需确认年报证据"
        else:
            status = "发现金额差异"

    if evidence is None or evidence.get("OCR中找到金额") != "是":
        page = ""
        evidence_text = ""
        evidence_status = "缺少年报定位证据"
    else:
        page = evidence.get("年报PDF页码", "")
        evidence_text = evidence.get("年报原文证据", "")
        evidence_status = evidence.get("核验状态", "待人工确认")

    return {
        "编号": claim["编号"],
        "研报说法": claim["研报说法"],
        "指标": indicator,
        "年份": year,
        "研报金额（元）": str(claim["金额_元"]),
        "标准金额（元）": standard_amount,
        "核查结果": status,
        "证据PDF页码": page,
        "证据核验状态": evidence_status,
        "年报证据片段": evidence_text,
    }


def main():
    evidence_rows = load_evidence()
    results = [
        check_claim(claim, evidence_rows)
        for claim in TEST_CLAIMS
    ]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(results[0].keys())

    with OUTPUT_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("研报说法核查完成！")

    for result in results:
        print(
            f"{result['编号']} | "
            f"{result['研报说法']} | "
            f"{result['核查结果']} | "
            f"证据页码：{result['证据PDF页码'] or '未定位'}"
        )

    print(f"详细结果已保存到：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
