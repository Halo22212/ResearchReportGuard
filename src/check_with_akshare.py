import os
import json
import akshare as ak

from metric_registry import (
    METRIC_REGISTRY, normalize_metric, get_spec,
    SRC_INCOME, SRC_ABSTRACT,
    TYPE_AMOUNT, TYPE_RATIO, TYPE_PER_SHARE,
    TYPE_TURNOVER_TIMES, TYPE_TURNOVER_DAYS,
)

# ============ 1. 公司名 → 股票代码 ============
print("正在加载 A 股代码表 ...")
_code_table = ak.stock_info_a_code_name()
_code_table["name_clean"] = _code_table["name"].str.replace(r"\s+", "", regex=True)

GENERIC_WORDS = [
    "股份有限公司", "有限责任公司", "有限公司", "集团", "股份",
    "控股", "实业", "公司", "企业",
    "内蒙古", "北京", "上海", "广州", "深圳", "广东", "浙江", "江苏",
    "山东", "福建", "湖北", "湖南", "四川", "陕西", "新疆", "西藏",
    "天津", "重庆", "安徽", "河南", "河北", "辽宁", "吉林", "黑龙江",
    "江西", "广西", "海南", "贵州", "云南", "甘肃", "青海", "宁夏",
    "山西", "中国",
]

def _clean_name(name):
    s = name
    for w in GENERIC_WORDS:
        s = s.replace(w, "")
    return s.strip()

def lookup_stock_code(company_name):
    if not company_name:
        return None, None, "空输入"
    q_clean = company_name.strip().replace(" ", "")

    m = _code_table[_code_table["name_clean"] == q_clean]
    if not m.empty:
        return m.iloc[0]["code"], m.iloc[0]["name"], "精确匹配"

    core = _clean_name(q_clean)
    if core and core != q_clean:
        m = _code_table[_code_table["name_clean"] == core]
        if not m.empty:
            return m.iloc[0]["code"], m.iloc[0]["name"], f"去通用词后精确匹配（{core}）"

    m = _code_table[_code_table["name_clean"].str.contains(q_clean, na=False, regex=False)]
    if m.empty and core:
        m = _code_table[_code_table["name_clean"].str.contains(core, na=False, regex=False)]
    if not m.empty:
        m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
        return m.iloc[0]["code"], m.iloc[0]["name"], "包含匹配"

    if core and len(core) >= 2:
        m = _code_table[_code_table["name_clean"].str.contains(core, na=False, regex=False)]
        if not m.empty:
            m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
            return m.iloc[0]["code"], m.iloc[0]["name"], f"品牌词匹配（{core}）"

    if core:
        for length in (4, 3, 2):
            for i in range(len(core) - length + 1):
                sub = core[i:i+length]
                m = _code_table[_code_table["name_clean"].str.contains(sub, na=False, regex=False)]
                if not m.empty:
                    m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
                    return m.iloc[0]["code"], m.iloc[0]["name"], f"子串匹配（{sub}）"

    return None, None, "未找到"

def to_sina_code(code):
    if code.startswith(("6", "9")):
        return "sh" + code
    return "sz" + code

# ============ 2. 单位换算 ============
UNIT_TO_YUAN = {"元": 1, "万元": 10_000, "亿元": 100_000_000, "万亿": 1_000_000_000_000}

def to_yuan(amount, unit):
    if amount is None or unit is None:
        return None
    unit = unit.strip()
    if unit not in UNIT_TO_YUAN:
        return None
    return amount * UNIT_TO_YUAN[unit]

def to_display_unit(yuan_val, target_unit):
    if yuan_val is None or target_unit is None:
        return None
    rate = UNIT_TO_YUAN.get(target_unit)
    if rate is None:
        return None
    return yuan_val / rate

# ============ 3. 数据缓存与读取 ============
_income_cache = {}
_abstract_cache = {}

def load_income_sheet(code):
    if code in _income_cache:
        return _income_cache[code]
    df = ak.stock_financial_report_sina(stock=to_sina_code(code), symbol="利润表")
    df["报告日_str"] = df["报告日"].astype(str).str.replace("-", "", regex=False)
    _income_cache[code] = df
    return df

def load_abstract(code):
    if code in _abstract_cache:
        return _abstract_cache[code]
    df = ak.stock_financial_abstract(symbol=code)
    _abstract_cache[code] = df
    return df

def get_financial_value(code, spec, report_date):
    src = spec["source"]
    field = spec["field"]

    if src == SRC_INCOME:
        try:
            df = load_income_sheet(code)
        except Exception as e:
            return None, field, f"利润表加载失败：{e}"
        row = df[df["报告日_str"] == report_date]
        if row.empty:
            return None, field, f"利润表无 {report_date} 数据"
        try:
            return float(row.iloc[0][field]), field, "利润表"
        except (TypeError, ValueError, KeyError) as e:
            return None, field, f"字段 '{field}' 无法读取：{e}"

    elif src == SRC_ABSTRACT:
        group = spec["group"]
        try:
            df = load_abstract(code)
        except Exception as e:
            return None, field, f"财务摘要加载失败：{e}"
        sub = df[(df["选项"] == group) & (df["指标"] == field)]
        if sub.empty:
            return None, field, f"财务摘要 {group}/{field} 未找到"
        try:
            return float(sub.iloc[0][report_date]), field, f"财务摘要·{group}"
        except (TypeError, ValueError, KeyError) as e:
            return None, field, f"该期无数据：{e}"

    return None, field, f"未知数据源：{src}"

# ============ 4. 按类型判断 ============
TOLERANCES = {
    TYPE_AMOUNT:        {"rel_ok": 0.001,  "rel_bad": 0.05},
    TYPE_RATIO:         {"abs_ok": 0.05,   "abs_bad": 0.5},
    TYPE_PER_SHARE:     {"rel_ok": 0.005,  "rel_bad": 0.05},
    TYPE_TURNOVER_TIMES:{"rel_ok": 0.01,   "rel_bad": 0.10},
    TYPE_TURNOVER_DAYS: {"rel_ok": 0.01,   "rel_bad": 0.10},
}

def judge_amount(claim_val, ref_val, metric_type):
    if claim_val is None or ref_val is None:
        return "无法判断（数值缺失）", None
    cfg = TOLERANCES.get(metric_type)
    if cfg is None:
        return "无法判断（未知指标类型）", None

    if "abs_ok" in cfg:
        diff = abs(claim_val - ref_val)
        if diff <= cfg["abs_ok"]:
            return "与财报一致", diff
        elif diff <= cfg["abs_bad"]:
            return "疑似错误，需人工复核", diff
        else:
            return "明显不一致", diff
    else:
        if ref_val == 0:
            return "无法判断（基准为 0）", None
        rel = abs(claim_val - ref_val) / abs(ref_val)
        if rel <= cfg["rel_ok"]:
            return "与财报一致", rel
        elif rel <= cfg["rel_bad"]:
            return "疑似错误，需人工复核", rel
        else:
            return "明显不一致", rel

# ---- 新增：按类型算同比 ----
def compute_yoy(ak_val, prev_val, metric_type):
    """
    比率类：返回"百分点差"（新% - 旧%）。
    其他类：返回"变化率"（(新-旧)/旧 × 100）。
    """
    if ak_val is None or prev_val in (None, 0):
        return None
    if metric_type == TYPE_RATIO:
        return ak_val - prev_val          # 百分点差
    else:
        return (ak_val - prev_val) / prev_val * 100

def judge_yoy(reported_pct, computed_pct):
    if reported_pct is None:
        return "原文未提供同比", None
    if computed_pct is None:
        return "无法自算同比（缺上年数据）", None
    diff = abs(reported_pct - computed_pct)
    if diff <= 0.01:
        return "一致", diff
    elif diff <= 0.5:
        return "疑似错误，需人工复核", diff
    else:
        return "明显不一致", diff

# ============ 5. 生成结论 ============
def format_value(v, metric_type):
    if v is None:
        return "—"
    if metric_type == TYPE_RATIO:
        return f"{v:.4f}%"
    if metric_type == TYPE_PER_SHARE:
        return f"{v:.4f} 元/股"
    if metric_type == TYPE_TURNOVER_TIMES:
        return f"{v:.4f} 次"
    if metric_type == TYPE_TURNOVER_DAYS:
        return f"{v:.4f} 天"
    return f"{v:,.2f} 元"

def make_verdict(metric, metric_type, amount_status, yoy_status,
                 claim_val, ref_val, year, computed_yoy, reported_yoy):
    if "暂不支持" in (amount_status or ""):
        return f"⏸️ {metric} 当前版本暂不支持自动核查", None
    if "未识别公司" in (amount_status or ""):
        return f"❓ {metric} 无法核查：公司未识别", None
    if "年份缺失" in (amount_status or ""):
        return f"❓ {metric} 无法核查：年份缺失", None

    if amount_status == "与财报一致":
        parts = [f"✅ {metric} 与财报一致"]
        if yoy_status == "一致":
            parts.append("同比也一致")
        elif yoy_status == "明显不一致":
            unit = "个百分点" if metric_type == TYPE_RATIO else "%"
            parts.append(f"⚠️ 但同比不一致（研报 {reported_yoy}{unit}，"
                         f"财报口径 {computed_yoy:.4f}{unit}）")
        return "；".join(parts), None

    if ref_val is not None:
        ref_disp = format_value(ref_val, metric_type)
        claim_disp = format_value(claim_val, metric_type)
        verdict = f"❌ {metric} 与财报不一致（{amount_status}）"
        if yoy_status == "明显不一致":
            verdict += "；同比也明显不一致"
        suggestion = (f"研报写 {claim_disp}，{year} 年财报实际值为 {ref_disp}。")
        if amount_status == "明显不一致":
            suggestion += "差异显著，建议核对原句或修改。"
        else:
            suggestion += "差异较小，建议核对原句与单位。"
        return verdict, suggestion

    return f"❓ {metric} 无法核查：{amount_status}", None

# ============ 6. 选择输入文件 ============
base_dir = os.path.dirname(os.path.abspath(__file__))
report_json = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "extracted_claims_from_report.json")
)
sentence_json = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "extracted_claims.json")
)

if os.path.exists(report_json):
    input_path = report_json
    print("输入来源：研报 PDF 抽取结果")
elif os.path.exists(sentence_json):
    input_path = sentence_json
    print("输入来源：手写句子抽取结果")
else:
    raise FileNotFoundError("找不到任何待核查 JSON")

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)
claims = data.get("claims", [])
if not claims:
    raise ValueError(f"{input_path} 里没有 claims")

print(f"共读取 {len(claims)} 条主张\n")

# ============ 7. 逐条核查 ============
results = []
skipped_forecast = 0

for c in claims:
    raw_metric = c.get("metric")
    metric = normalize_metric(raw_metric)
    spec = get_spec(metric)
    year = c.get("year")
    amount = c.get("amount")
    unit = c.get("unit")
    reported_yoy = c.get("yoy_percent")
    company_in_claim = c.get("company")
    page = c.get("page")
    is_forecast = c.get("is_forecast", False)

    if is_forecast:
        skipped_forecast += 1
        print("=" * 68)
        print("🔮 [跳过] 预测性陈述")
        print(f"   原句：{c.get('source_text')}")
        if page:
            print(f"   页码：第 {page} 页")
        continue

    code, matched_name, match_method = lookup_stock_code(company_in_claim)

    ak_val = prev_val = computed_yoy = None
    field_used = data_source = metric_type = ""
    amount_status = yoy_status = ""
    amount_rel = yoy_diff = None

    if spec is None:
        amount_status = f"当前版本暂不支持该指标：{raw_metric}"
        yoy_status = "当前版本暂不支持该指标"
    elif code is None:
        amount_status = f"未识别公司：{company_in_claim}"
        yoy_status = "未识别公司"
    elif year is None:
        amount_status = "年份缺失"
        yoy_status = "年份缺失"
    else:
        metric_type = spec["type"]
        cur_date = f"{year}1231"
        prev_date = f"{year-1}1231"

        ak_val, field_used, data_source = get_financial_value(code, spec, cur_date)
        prev_val, _, _ = get_financial_value(code, spec, prev_date)

        if ak_val is None:
            amount_status = f"无法自动核查：{field_used}"
        elif metric_type == TYPE_AMOUNT:
            claim_yuan = to_yuan(amount, unit)
            amount_status, amount_rel = judge_amount(claim_yuan, ak_val, metric_type)
        else:
            amount_status, amount_rel = judge_amount(amount, ak_val, metric_type)

        # ---- 关键修复：按类型算同比 ----
        computed_yoy = compute_yoy(ak_val, prev_val, metric_type)
        yoy_status, yoy_diff = judge_yoy(reported_yoy, computed_yoy)

    verdict, suggestion = make_verdict(
        metric, metric_type or TYPE_AMOUNT, amount_status, yoy_status,
        amount, ak_val, year, computed_yoy, reported_yoy
    )

    result = {
        "page": page,
        "company_raw": company_in_claim,
        "company_matched_code": code,
        "company_matched_name": matched_name,
        "company_match_method": match_method,
        "raw_metric": raw_metric,
        "metric": metric,
        "metric_type": metric_type,
        "year": year,
        "amount": amount,
        "unit": unit,
        "amount_yuan": to_yuan(amount, unit) if metric_type == TYPE_AMOUNT else None,
        "akshare_value_yuan": ak_val if metric_type == TYPE_AMOUNT else None,
        "akshare_value_raw": ak_val,
        "akshare_prev_value_yuan": prev_val,
        "data_source": data_source,
        "field_used": field_used,
        "amount_relative_diff": amount_rel,
        "amount_status": amount_status,
        "reported_yoy_percent": reported_yoy,
        "computed_yoy_percent": computed_yoy,
        "yoy_diff_pct": yoy_diff,
        "yoy_status": yoy_status,
        "verdict": verdict,
        "suggestion": suggestion,
        "source_text": c.get("source_text"),
    }
    results.append(result)

    page_str = f"[p{page}] " if page else ""
    print("=" * 68)
    print(f"{page_str}原句：{result['source_text']}")
    if code:
        print(f"公司： '{company_in_claim}' → {code} ({matched_name}) [{match_method}]")
    print(f"指标：{raw_metric}（类型：{metric_type or '未知'}）")
    print("结论：", verdict)
    if ak_val is not None:
        print(f"财报值：{format_value(ak_val, metric_type)}（{data_source} · {field_used}）")
    if computed_yoy is not None:
        yoy_unit = "个百分点" if metric_type == TYPE_RATIO else "%"
        print(f"自算同比：{computed_yoy:.4f}{yoy_unit}（研报：{reported_yoy}{yoy_unit}）")
    if suggestion:
        print("修改建议：", suggestion)

# ============ 8. 汇总 ============
print("\n" + "=" * 68)
print("汇总")
print("=" * 68)
for r in results:
    page_s = f"p{r['page']}" if r.get("page") else "-"
    print(f"{page_s:<4}{(r['metric'] or '')[:30]:<32}{(r['verdict'] or '')[:60]}")

if skipped_forecast:
    print(f"\n（另有 {skipped_forecast} 条预测性陈述被跳过）")

# ============ 9. 保存 ============
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "claim_check_with_akshare.json")
)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n结果已保存到：")
print(output_path)