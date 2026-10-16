import os
import json
from datetime import datetime

base_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "claim_check_with_akshare.json")
)
output_path = os.path.abspath(
    os.path.join(base_dir, "..", "outputs", "check_report.md")
)

with open(input_path, "r", encoding="utf-8") as f:
    results = json.load(f)

if not results:
    raise ValueError("核查结果为空，请先运行 check_with_akshare.py")

# ---- 统计 ----
total = len(results)
n_ok = sum(1 for r in results if "✅" in (r.get("verdict") or ""))
n_bad = sum(1 for r in results if "❌" in (r.get("verdict") or ""))
n_unk = sum(1 for r in results if "❓" in (r.get("verdict") or ""))
n_skip = sum(1 for r in results if "⏸️" in (r.get("verdict") or ""))

# ---- 生成 Markdown ----
lines = []
lines.append("# 研报核查报告")
lines.append("")
lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("")
lines.append("## 一、核查概览")
lines.append("")
lines.append(f"- 共核查 **{total}** 条财务陈述")
lines.append(f"- ✅ 与财报一致：**{n_ok}** 条")
lines.append(f"- ❌ 疑似错误 / 明显不一致：**{n_bad}** 条")
lines.append(f"- ❓ 无法自动核查：**{n_unk}** 条")
lines.append(f"- ⏸️ 当前版本暂不支持：**{n_skip}** 条")
lines.append("")
lines.append("## 二、核查明细")
lines.append("")

for i, r in enumerate(results, 1):
    page = r.get("page")
    page_str = f"（第 {page} 页）" if page else ""
    lines.append(f"### {i}. {r.get('metric')} {page_str}")
    lines.append("")
    lines.append(f"**研报原句**：{r.get('source_text')}")
    lines.append("")
    lines.append(f"**结论**：{r.get('verdict')}")
    lines.append("")

    # 金额对比
    amount = r.get("amount")
    unit = r.get("unit")
    ak_val = r.get("akshare_value_yuan")
    if amount is not None and ak_val is not None:
        from_ak = None
        rate = {"元": 1, "万元": 1e4, "亿元": 1e8, "万亿": 1e12}.get(unit)
        if rate:
            from_ak = ak_val / rate
        lines.append("| 项目 | 研报 | 财报实际值 |")
        lines.append("|---|---|---|")
        lines.append(f"| {r.get('metric')}（{r.get('year')} 年） "
                     f"| {amount} {unit} "
                     f"| {from_ak:,.2f} {unit} |"
                     if from_ak is not None
                     else f"| {r.get('metric')}（{r.get('year')} 年） "
                          f"| {amount} {unit} | — |")
        lines.append("")

    # 同比对比
    rep_yoy = r.get("reported_yoy_percent")
    comp_yoy = r.get("computed_yoy_percent")
    if rep_yoy is not None and comp_yoy is not None:
        lines.append("| 同比 | 研报 | 财报口径自算 |")
        lines.append("|---|---|---|")
        lines.append(f"| 同比变化 | {rep_yoy}% | {comp_yoy:.2f}% |")
        lines.append("")

    # 证据
    lines.append("**证据来源**：")
    lines.append(f"- 数据源：{r.get('data_source')}（字段：{r.get('field_used')}）")
    if r.get("company_matched_code"):
        lines.append(f"- 公司：{r.get('company_matched_name')}"
                     f"（{r.get('company_matched_code')}）"
                     f"，匹配方式：{r.get('company_match_method')}")
    if page:
        lines.append(f"- 研报页码：第 {page} 页")
    lines.append("")

    # 修改建议
    if r.get("suggestion"):
        lines.append("**修改建议**：")
        lines.append("")
        lines.append(f"> {r.get('suggestion')}")
        lines.append("")

    lines.append("---")
    lines.append("")

lines.append("## 三、说明")
lines.append("")
lines.append("- 核查基准：A 股上市公司公开财报数据（AkShare 数据源）。")
lines.append("- 一致判定：金额相对差 ≤ 0.1%；同比差 ≤ 0.01 个百分点。")
lines.append("- 疑似错误：0.1% < 金额相对差 ≤ 5%；0.01 < 同比差 ≤ 0.5 个百分点。")
lines.append("- 明显不一致：金额相对差 > 5%；同比差 > 0.5 个百分点。")
lines.append("- 预测性陈述（含\"预计\"\"有望\"等）不参与核查。")
lines.append("- 本报告为自动生成，重要结论建议人工复核。")

content = "\n".join(lines)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"核查报告已生成：{output_path}")
print(f"共 {total} 条，其中 ✅ {n_ok} / ❌ {n_bad} / ❓ {n_unk} / ⏸️ {n_skip}")
print()
print("=" * 68)
print("预览（前 60 行）")
print("=" * 68)
for line in content.split("\n")[:60]:
    print(line)