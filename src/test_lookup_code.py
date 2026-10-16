import akshare as ak

print("正在下载 A 股代码表...")
table = ak.stock_info_a_code_name()

# 归一化表里的名字（去多余空格）
table["name_clean"] = table["name"].str.replace(r"\s+", "", regex=True)

# 通用词：地域、组织、行业
GENERIC_WORDS = [
    # 组织/后缀
    "股份有限公司", "有限责任公司", "有限公司", "集团", "股份",
    "控股", "实业", "公司", "企业",
    # 地域
    "内蒙古", "北京", "上海", "广州", "深圳", "广东", "浙江", "江苏",
    "山东", "福建", "湖北", "湖南", "四川", "陕西", "新疆", "西藏",
    "天津", "重庆", "安徽", "河南", "河北", "辽宁", "吉林", "黑龙江",
    "江西", "广西", "海南", "贵州", "云南", "甘肃", "青海", "宁夏",
    "山西", "中国",
]

def clean_name(name):
    """去掉通用词，保留核心品牌词。"""
    s = name
    for w in GENERIC_WORDS:
        s = s.replace(w, "")
    return s.strip()

def find_stock_code(company_name):
    if not company_name:
        return None, None, "空输入"

    q = company_name.strip()
    q_clean = q.replace(" ", "")

    # 1. 精确匹配（含归一化）
    m = table[table["name_clean"] == q_clean]
    if not m.empty:
        return m.iloc[0]["code"], m.iloc[0]["name"], "精确匹配"

    # 2. 去通用词后，精确匹配
    core = clean_name(q_clean)
    if core and core != q_clean:
        m = table[table["name_clean"] == core]
        if not m.empty:
            return m.iloc[0]["code"], m.iloc[0]["name"], f"去通用词后精确匹配（{core}）"

    # 3. 表里名字包含查询串（双向包含）
    m = table[table["name_clean"].str.contains(q_clean, na=False, regex=False)]
    if m.empty and core:
        m = table[table["name_clean"].str.contains(core, na=False, regex=False)]
    if not m.empty:
        m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
        return m.iloc[0]["code"], m.iloc[0]["name"], "包含匹配"

    # 4. 用核心品牌词做包含匹配
    if core and len(core) >= 2:
        m = table[table["name_clean"].str.contains(core, na=False, regex=False)]
        if not m.empty:
            m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
            return m.iloc[0]["code"], m.iloc[0]["name"], f"品牌词匹配（{core}）"

    # 5. 从核心词里逐个提取 2-4 字的候选子串
    if core:
        for length in (4, 3, 2):
            for i in range(len(core) - length + 1):
                sub = core[i:i+length]
                m = table[table["name_clean"].str.contains(sub, na=False, regex=False)]
                if not m.empty:
                    m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
                    return m.iloc[0]["code"], m.iloc[0]["name"], f"子串匹配（{sub}）"

    return None, None, "未找到"

test_names = [
    "伊利股份",
    "内蒙古伊利实业集团股份有限公司",
    "伊利",
    "贵州茅台",
    "招商银行",
    "宁德时代",
    "中国平安",
    "不存在的公司XYZ",
]

print("\n" + "=" * 78)
print("公司名匹配测试")
print("=" * 78)
for name in test_names:
    code, matched_name, how = find_stock_code(name)
    if code:
        print(f"  {name:<36} → {code}  ({matched_name})  [{how}]")
    else:
        print(f"  {name:<36} → 未找到  [{how}]")