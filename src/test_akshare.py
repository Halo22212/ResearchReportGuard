import akshare as ak

# 伊利股份股票代码：600887（上海主板）
print("=" * 60)
print("尝试 1：同花顺 - 主要财务指标（按年度）")
print("=" * 60)
try:
    df = ak.stock_financial_abstract_ths(symbol="600887", indicator="按年度")
    print("列名：", list(df.columns))
    print(df.head(5).to_string())
except Exception as e:
    print("失败：", type(e).__name__, "-", e)

print()
print("=" * 60)
print("尝试 2：新浪 - 财务摘要")
print("=" * 60)
try:
    df2 = ak.stock_financial_abstract(symbol="600887")
    print("列名：", list(df2.columns))
    print(df2.head(30).to_string())
except Exception as e:
    print("失败：", type(e).__name__, "-", e)