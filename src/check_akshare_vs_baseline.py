import akshare as ak

# ---- 人工基准（单位：元）----
BASELINE = {
    "营业收入": 115636231250.05,
    "归属于上市公司股东的净利润": 11565166497.81,
    "归属于上市公司股东的扣除非经常性损益的净利润": 11068321695.12,
    "经营活动产生的现金流量净额": 14343920490.32,
    "利润总额": 12993830374.42,
}

# AkShare 字段名 → 我们的人工基准名
AKSHARE_FIELD_MAP = {
    "营业收入": "营业总收入",
    "归属于上市公司股东的净利润": "归母净利润",
    "归属于上市公司股东的扣除非经常性损益的净利润": "扣非净利润",
    "经营活动产生的现金流量净额": "经营现金流量净额",
    "利润总额": None,   # AkShare 新浪接口没有这个字段
}

REPORT_DATE = "20251231"
OPTION_GROUP = "常用指标"   # 限定在这个分组里取，避免重名

print("=" * 92)
print(f"AkShare 新浪财务摘要 vs 人工基准  （报告期：{REPORT_DATE}，分组：{OPTION_GROUP}）")
print("=" * 92)

df = ak.stock_financial_abstract(symbol="600887")

# 只保留"常用指标"分组
df_common = df[df["选项"] == OPTION_GROUP].copy()

print(f"\n{'指标（年报口径）':<44}{'AkShare值':>22}{'人工基准':>22}{'相对差':>12}")
print("-" * 100)

for base_name, ak_name in AKSHARE_FIELD_MAP.items():
    base_val = BASELINE[base_name]

    if ak_name is None:
        print(f"{base_name:<44}{'—（无对应字段）':>22}{base_val:>22,.2f}{'—':>12}")
        continue

    row = df_common[df_common["指标"] == ak_name]
    if row.empty:
        print(f"{base_name:<44}{'—（字段缺失）':>22}{base_val:>22,.2f}{'—':>12}")
        continue

    try:
        ak_val = float(row.iloc[0][REPORT_DATE])
        rel = abs(ak_val - base_val) / base_val
        print(f"{base_name:<44}{ak_val:>22,.2f}{base_val:>22,.2f}{rel:>11.4%}")
    except (TypeError, ValueError) as e:
        print(f"{base_name:<44}无法转换：{e}")

print()
print("说明：")
print("- AkShare 值来自新浪财务摘要，单位：元")
print("- 相对差 > 0.1% 说明两个口径可能不一致，需人工判断")
print("- 重点看 '营业总收入' vs 人工基准的 '营业收入' 差多少")