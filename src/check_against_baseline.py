import os
import json

# ============ 1. 指标别名表 ============
METRIC_ALIASES = {
    "营业收入": "营业收入",
    "利润总额": "利润总额",
    "归属于上市公司股东的净利润": "归属于上市公司股东的净利润",
    "归母净利润": "归属于上市公司股东的净利润",
    "归属于母公司股东的净利润": "归属于上市公司股东的净利润",
    "归属于上市公司股东的扣除非经常性损益的净利润":
        "归属于上市公司股东的扣除非经常性损益的净利润",
    "扣非归母净利润": "归属于上市公司股东的扣除非经常性损益的净利润",
    "扣非净利润": "归属于上市公司股东的扣除非经常性损益的净利润",
    "经营活动产生的现金流量净额": "经营活动产生的现金流量净额",
    "经营活动现金流量净额": "经营活动产生的现金流量净额",
    "经营现金流": "经营活动产生的现金流量净额",
    "经营现金流净额": "经营活动产生的现金流量净额",
}

def normalize_metric(name):
    if name is None:
        return None
    return METRIC_ALIASES.get(name.strip(), name.strip())

# ============ 2. 阈值 ============
TOLERANCE_AMOUNT_CONSISTENT = 0.001
TOLERANCE_AMOUNT_SUSPICIOUS = 0.05
TOLERANCE_YOY_CONSISTENT = 0.01
TOLERANCE_YOY_SUSPICIOUS = 0.5

# ============ 3. 单位换算 ============
UNIT_TO_YUAN = {"元": 1, "万元": 10_000, "亿元": 100_000_000, "万亿": 1_000_000_000_000}

def to_yuan(amount, unit):
    if amount is None or unit is None:
        return None
    unit = unit.strip()
    if unit not in UNIT_TO_YUAN:
        return None
    return amount * UNIT_TO_YUAN[unit]

# ============ 4. 解析人工核实证据文件 ============
def load_evidence_file(path):
    """读取 evidence_page_*.txt，返回：
    - baseline: {(metric, year): float}    单位：元
    - yoy:      {(metric, year): float}    百分点（0.21 表示 0.21%）
    - text:     文件里 # 开头的注释行列表（用于元信息）
    """
    baseline = {}
    yoy = {}
    comment_lines = []
    current_metric = None

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("#"):
                comment_lines.append(stripped.lstrip("#").strip())
                continue

            if stripped.startswith("metric:"):
                current_metric = stripped.split(":", 1)[1].strip()
                continue

            if current_metric and ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()
                try:
                    if key in ("2023", "2024", "2025"):
                        baseline[(current_metric, int(key))] = float(val.replace(",", ""))
                    elif key.startswith("yoy_pct_"):
                        year = int(key.replace("yoy_pct_", ""))
                        yoy[(current_metric, year)] = float(val.replace(",", ""))
                except ValueError:
                    print(f"⚠️ 跳过无法解析的行：{stripped}")

    return baseline, yoy, comment_lines

# ============ 5. 判断函数 ============
def judge_amount(claim_yuan, baseline_yuan):
    if claim_yuan is None or baseline_yuan in (None, 0):
        return "无法判断（数值或基准缺失）", None
    rel = abs(claim_yuan - baseline_yuan) / abs(baseline_yuan)
    if rel <= TOLERANCE_AMOUNT_CONSISTENT:
        return "与年报一致（在合理精度范围内）", rel
    elif rel <= TOLERANCE_AMOUNT_SUSPICIOUS:
        return "疑似错误，需人工复核", rel
    else:
        return "明显不一致", rel

def judge_yoy_pct(reported_pct, reference_pct):
    if reported_pct is None or reference_pct is None:
        return "无法判断（数值或基准缺失）", None
    diff = abs(reported_pct - reference_pct)
    if diff <= TOLERANCE_YOY_CONSISTENT:
        return "一致", diff
    elif diff <= TOLERANCE_YOY_SUSPICIOUS:
        return "疑似错误，需人工复核", diff
    else:
        return "明显不一致", diff

# ============ 6. 路径 ============
base_dir = os.path.dirname(os.path.abspath(__file__))

evidence_text_path = os.path.abspath(
    os.path.join(base_dir, "..", "data", "evidence", "evidence_page_7.txt")
)
evidence_image_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "evidence", "page_7_table.png")
)
input_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "extracted_claims.json")
)

for p in (evidence_text_path, evidence_image_path, input_path):
    if not os.path.exists(p):
        raise FileNotFoundError(f"找不到文件：{p}")

# ============ 7. 加载证据与提取结果 ============
BASELINE, BASELINE_YOY_PCT, _ = load_evidence_file(evidence_text_path)

print("已从证据文件加载基准数据：")
for (m, y), v in sorted(BASELINE.items()):
    print(f"  {m}  {y}: {v}")
print()

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

claims = data.get("claims", [])
if not claims:
    raise ValueError("extracted_claims.json 里没有 claims，请先运行 extract_claims.py")

# OCR 可靠性说明（记录为何采用人工核实文本）
EVIDENCE_OCR_STATUS = {
    ("营业收入", 2025): (True, ""),
    ("利润总额", 2025): (False, "OCR 仅识别出 \". 42\"，整数部分缺失"),
    ("归属于上市公司股东的净利润", 2025): (True, ""),
    ("归属于上市公司股东的扣除非经常性损益的净利润", 2025):
        (False, "OCR 仅识别出 \"0\"，数字全部缺失"),
    ("经营活动产生的现金流量净额", 2025):
        (False, "OCR 识别为 \"14， 343, 920, 490, 32\"，含中文逗号且小数位错"),
}

EVIDENCE_PAGE = 7
EVIDENCE_SOURCE = "年报第 7 页 · 七、近三年主要会计数据和财务指标 → (一)主要会计数据"

# ============ 8. 逐条比对 ============
results = []
for c in claims:
    raw_metric = c.get("metric")
    metric = normalize_metric(raw_metric)
    year = c.get("year")
    amount = c.get("amount")
    unit = c.get("unit")
    reported_yoy_pct = c.get("yoy_percent")

    # ---- 金额 ----
    claim_yuan = to_yuan(amount, unit)
    baseline_yuan = BASELINE.get((metric, year))
    amount_status, amount_rel = judge_amount(claim_yuan, baseline_yuan)

    # ---- 同比：参照 1 = 年报披露 ----
    disclosed_pct = BASELINE_YOY_PCT.get((metric, year))

    # ---- 同比：参照 2 = 用年报两年金额自算 ----
    v_cur = BASELINE.get((metric, year))
    v_prev = BASELINE.get((metric, year - 1))
    if v_cur is not None and v_prev not in (None, 0):
        computed_pct = (v_cur - v_prev) / v_prev * 100
    else:
        computed_pct = None

    yoy_vs_disclosed_status, yoy_vs_disclosed_diff = judge_yoy_pct(
        reported_yoy_pct, disclosed_pct
    )
    computed_vs_disclosed_status, computed_vs_disclosed_diff = judge_yoy_pct(
        computed_pct, disclosed_pct
    )

    ocr_ok, ocr_note = EVIDENCE_OCR_STATUS.get((metric, year), (None, "无 OCR 可靠性记录"))

    result = {
        "company": c.get("company"),
        "raw_metric": raw_metric,
        "metric": metric,
        "year": year,
        "amount": amount,
        "unit": unit,
        "amount_yuan": claim_yuan,
        "baseline_yuan": baseline_yuan,
        "amount_relative_diff": amount_rel,
        "amount_status": amount_status,
        "reported_yoy_percent": reported_yoy_pct,
        "disclosed_yoy_percent": disclosed_pct,
        "computed_yoy_percent": computed_pct,
        "yoy_vs_disclosed_diff_pct": yoy_vs_disclosed_diff,
        "yoy_vs_disclosed_status": yoy_vs_disclosed_status,
        "computed_vs_disclosed_diff_pct": computed_vs_disclosed_diff,
        "computed_vs_disclosed_status": computed_vs_disclosed_status,
        "source_text": c.get("source_text"),
        # ---- 证据 ----
        "evidence_page": EVIDENCE_PAGE,
        "evidence_source": EVIDENCE_SOURCE,
        "evidence_text_file": os.path.relpath(evidence_text_path, os.path.dirname(base_dir)),
        "evidence_image_file": os.path.relpath(evidence_image_path, os.path.dirname(base_dir)),
        "evidence_ocr_ok": ocr_ok,
        "evidence_ocr_note": ocr_note,
    }
    results.append(result)

    print("=" * 64)
    print("公司：", result["company"])
    print("指标：", raw_metric, ("→ " + metric) if metric != raw_metric else "")
    print("年份：", year)
    print("--- 金额核验 ---")
    print("研报金额：", amount, unit, " → 换算：", claim_yuan, "元")
    print("年报基准：", baseline_yuan, "元")
    if amount_rel is not None:
        print("相对差：{:.6%}".format(amount_rel))
    print("金额状态：", amount_status)
    print("--- 同比核验 ---")
    print("研报同比：{}%  年报披露：{}%".format(reported_yoy_pct, disclosed_pct))
    if computed_pct is not None:
        print("自算同比：{:.6f}%".format(computed_pct))
    print("研报 vs 披露：", yoy_vs_disclosed_status,
          "" if yoy_vs_disclosed_diff is None else
          "（差 {:.4f} 个百分点）".format(yoy_vs_disclosed_diff))
    print("自算 vs 披露：", computed_vs_disclosed_status,
          "" if computed_vs_disclosed_diff is None else
          "（差 {:.4f} 个百分点）".format(computed_vs_disclosed_diff))
    print("--- 年报依据 ---")
    print("来源：", EVIDENCE_SOURCE, "（页码", EVIDENCE_PAGE, "）")
    print("文本证据：", result["evidence_text_file"])
    print("可视证据：", result["evidence_image_file"])
    if ocr_ok is True:
        print("OCR 可靠性：可靠（与人工核实文本一致）")
    elif ocr_ok is False:
        print("OCR 可靠性：⚠️ 不可靠 —", ocr_note)
        print("           已改用人工核实文本作为基准")
    else:
        print("OCR 可靠性：未记录")

# ============ 9. 汇总 ============
print("\n" + "=" * 64)
print("汇总")
print("=" * 64)
print(f"{'指标':<26}{'金额状态':<24}{'同比':<12}{'OCR':<6}")
for r in results:
    metric_short = (r["metric"] or "")[:24]
    ocr_flag = "✅" if r["evidence_ocr_ok"] is True else (
        "⚠️" if r["evidence_ocr_ok"] is False else "?"
    )
    print(f"{metric_short:<26}{r['amount_status'] or '':<24}"
          f"{r['yoy_vs_disclosed_status'] or '':<12}{ocr_flag:<6}")

# ============ 10. 保存 ============
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "claim_check_against_baseline.json")
)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n结果已保存到：")
print(output_path)