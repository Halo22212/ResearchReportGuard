import akshare as ak

# ============ 1. 财务摘要 ============
print("=" * 78)
print("财务摘要 stock_financial_abstract（伊利率 600887）")
print("=" * 78)

df = ak.stock_financial_abstract(symbol="600887")
for group in df["选项"].unique():
    sub = df[df["选项"] == group]
    print(f"\n--- 分组：{group}（{len(sub)} 个指标）---")
    for _, row in sub.iterrows():
        metric = row["指标"]
        v25 = row.get("20251231", None)
        v24 = row.get("20241231", None)
        print(f"  {metric:<30} 2025={v25}  |  2024={v24}")

# ============ 2. 利润表 ============
print("\n" + "=" * 78)
print("利润表 stock_financial_report_sina")
print("=" * 78)

inc = ak.stock_financial_report_sina(stock="sh600887", symbol="利润表")
inc["报告日_str"] = inc["报告日"].astype(str).str.replace("-", "", regex=False)

row25 = inc[inc["报告日_str"] == "20251231"]
row24 = inc[inc["报告日_str"] == "20241231"]

r25 = row25.iloc[0] if not row25.empty else None
r24 = row24.iloc[0] if not row24.empty else None

print(f"\n利润表共 {len(inc.columns)} 列。每列 2025 / 2024 值：\n")
for col in inc.columns:
    if col in ("报告日", "报告日_str"):
        continue
    v25 = r25[col] if r25 is not None else "—"
    v24 = r24[col] if r24 is not None else "—"
    # 数值格式化
    try:
        if v25 != "—":
            v25 = f"{float(v25):,.2f}"
        if v24 != "—":
            v24 = f"{float(v24):,.2f}"
    except (ValueError, TypeError):
        pass
    print(f"  {col:<30} 2025={v25}  |  2024={v24}")