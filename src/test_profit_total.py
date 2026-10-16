import akshare as ak
import pandas as pd

df = ak.stock_financial_report_sina(stock="sh600887", symbol="利润表")

# 报告日字段看看长什么样
print("报告日前 12 个值：", df["报告日"].head(12).tolist())

key_cols = ["报告日", "营业总收入", "营业收入", "利润总额"]
print("\n前 12 行关键字段：")
print(df[key_cols].head(12).to_string())

# 找 2025-12-31（年报期）
print("\n" + "=" * 60)
print("查找 2025 年报期")
print("=" * 60)

df["报告日_str"] = df["报告日"].astype(str)
# 兼容两种格式：20251231 / 2025-12-31
mask = df["报告日_str"].str.replace("-", "", regex=False) == "20251231"
target = df[mask]

if target.empty:
    print("没找到 20251231，退化为看 2025 所有行：")
    print(df[df["报告日_str"].str.startswith("2025")][key_cols].to_string())
else:
    row = target.iloc[0]
    print("找到 2025-12-31：")
    print(f"  营业总收入：{row['营业总收入']:,.2f}")
    print(f"  营业收入：  {row['营业收入']:,.2f}")
    print(f"  利润总额：  {row['利润总额']:,.2f}")

    # ---- 口径基线计算 ----
    print("\n" + "=" * 60)
    print("口径基线计算（伊利）")
    print("=" * 60)

    total_rev = float(row["营业总收入"])
    op_rev = float(row["营业收入"])
    diff = (total_rev - op_rev) / total_rev

    print(f"营业总收入 {total_rev:,.2f}")
    print(f"营业收入   {op_rev:,.2f}")
    print(f"相对差：(总-营)/总 = {diff:.4%}")

    # 人工年报基准（元）
    MANUAL_REV = 115636231250.05
    print(f"\n人工年报营业收入：{MANUAL_REV:,.2f}")

    # 谁更接近人工基准？
    d_total = abs(total_rev - MANUAL_REV) / MANUAL_REV
    d_op = abs(op_rev - MANUAL_REV) / MANUAL_REV
    print(f"营业总收入 vs 人工基准：{d_total:.4%}")
    print(f"营业收入   vs 人工基准：{d_op:.4%}")
    print()
    if d_op < d_total:
        print("→ 利润表的 '营业收入' 字段与年报口径一致")
    else:
        print("→ 利润表的 '营业总收入' 字段与年报口径一致（不太常见）")

# ---- 顺便看利润总额多年数据，验证接法 ----
print("\n" + "=" * 60)
print("利润总额近 6 期（供核查脚本接用）")
print("=" * 60)
print(df[["报告日", "利润总额"]].head(6).to_string())