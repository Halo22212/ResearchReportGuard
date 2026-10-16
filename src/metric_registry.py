"""
指标注册表：定义每个指标的数据源、字段、类型、别名。
新增指标只需在此文件加一条，不用改核查脚本。
"""

# ---- 指标类型 ----
TYPE_AMOUNT = "amount"            # 金额，元
TYPE_RATIO = "ratio"              # 比率，%
TYPE_PER_SHARE = "per_share"      # 每股，元/股
TYPE_TURNOVER_TIMES = "turnover_times"    # 周转率，次
TYPE_TURNOVER_DAYS = "turnover_days"      # 周转天数，天

# ---- 数据源 ----
SRC_INCOME = "income_sheet"       # 利润表 stock_financial_report_sina
SRC_ABSTRACT = "abstract"         # 财务摘要 stock_financial_abstract（需指定 group）

# ---- 注册表 ----
# 每条：
#   aliases  —— 研报里可能的写法（含规范名本身）
#   source   —— 数据源
#   group    —— 仅 SRC_ABSTRACT 需要，取自 df["选项"]
#   field    —— 接口里的字段名
#   type     —— 指标类型
METRIC_REGISTRY = {
    # ============ 金额类（利润表）============
    "营业收入": {
        "aliases": ["营业收入", "营收"],
        "source": SRC_INCOME,
        "field": "营业收入",
        "type": TYPE_AMOUNT,
    },
    "营业成本": {
        "aliases": ["营业成本", "营业总成本"],
        "source": SRC_INCOME,
        "field": "营业成本",
        "type": TYPE_AMOUNT,
    },
    "营业利润": {
        "aliases": ["营业利润"],
        "source": SRC_INCOME,
        "field": "营业利润",
        "type": TYPE_AMOUNT,
    },
    "利润总额": {
        "aliases": ["利润总额"],
        "source": SRC_INCOME,
        "field": "利润总额",
        "type": TYPE_AMOUNT,
    },
    "所得税费用": {
        "aliases": ["所得税费用", "所得税"],
        "source": SRC_INCOME,
        "field": "所得税费用",
        "type": TYPE_AMOUNT,
    },
    "研发费用": {
        "aliases": ["研发费用", "研发投入"],
        "source": SRC_INCOME,
        "field": "研发费用",
        "type": TYPE_AMOUNT,
    },
    "销售费用": {
        "aliases": ["销售费用"],
        "source": SRC_INCOME,
        "field": "销售费用",
        "type": TYPE_AMOUNT,
    },
    "管理费用": {
        "aliases": ["管理费用"],
        "source": SRC_INCOME,
        "field": "管理费用",
        "type": TYPE_AMOUNT,
    },
    "财务费用": {
        "aliases": ["财务费用"],
        "source": SRC_INCOME,
        "field": "财务费用",
        "type": TYPE_AMOUNT,
    },

    # ============ 金额类（财务摘要）============
    "归属于上市公司股东的净利润": {
        "aliases": ["归属于上市公司股东的净利润", "归母净利润", "归母净利", "归属净利润"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "归母净利润",
        "type": TYPE_AMOUNT,
    },
    "归属于上市公司股东的扣除非经常性损益的净利润": {
        "aliases": [
            "归属于上市公司股东的扣除非经常性损益的净利润",
            "扣非归母净利润", "扣非净利润", "扣非净利",
        ],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "扣非净利润",
        "type": TYPE_AMOUNT,
    },
    "净利润": {
        "aliases": ["净利润"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "净利润",
        "type": TYPE_AMOUNT,
    },
    "经营活动产生的现金流量净额": {
        "aliases": [
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额",
            "经营现金流", "经营现金流净额", "经营现金流量净额",
        ],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "经营现金流量净额",
        "type": TYPE_AMOUNT,
    },

    # ============ 比率类（%）============
    "毛利率": {
        "aliases": ["毛利率", "销售毛利率"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "毛利率",
        "type": TYPE_RATIO,
    },
    "销售净利率": {
        "aliases": ["销售净利率", "净利率"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "销售净利率",
        "type": TYPE_RATIO,
    },
    "净资产收益率": {
        "aliases": ["净资产收益率", "净资产收益率(ROE)", "ROE"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "净资产收益率(ROE)",
        "type": TYPE_RATIO,
    },
    "总资产报酬率": {
        "aliases": ["总资产报酬率", "总资产报酬率(ROA)", "ROA"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "总资产报酬率(ROA)",
        "type": TYPE_RATIO,
    },
    "资产负债率": {
        "aliases": ["资产负债率"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "资产负债率",
        "type": TYPE_RATIO,
    },
    "期间费用率": {
        "aliases": ["期间费用率"],
        "source": SRC_ABSTRACT,
        "group": "常用指标",
        "field": "期间费用率",
        "type": TYPE_RATIO,
    },

    # ============ 每股类 ============
    "基本每股收益": {
        "aliases": ["基本每股收益", "每股收益", "EPS"],
        "source": SRC_ABSTRACT,
        "group": "每股指标",
        "field": "基本每股收益",
        "type": TYPE_PER_SHARE,
    },
    "稀释每股收益": {
        "aliases": ["稀释每股收益"],
        "source": SRC_ABSTRACT,
        "group": "每股指标",
        "field": "稀释每股收益",
        "type": TYPE_PER_SHARE,
    },
    "每股净资产": {
        "aliases": ["每股净资产"],
        "source": SRC_ABSTRACT,
        "group": "每股指标",
        "field": "每股净资产",
        "type": TYPE_PER_SHARE,
    },
    "每股经营现金流": {
        "aliases": ["每股经营现金流", "每股现金流"],
        "source": SRC_ABSTRACT,
        "group": "每股指标",
        "field": "每股经营现金流",
        "type": TYPE_PER_SHARE,
    },

    # ============ 营运能力 ============
    "存货周转率": {
        "aliases": ["存货周转率"],
        "source": SRC_ABSTRACT,
        "group": "营运能力",
        "field": "存货周转率",
        "type": TYPE_TURNOVER_TIMES,
    },
    "应收账款周转率": {
        "aliases": ["应收账款周转率"],
        "source": SRC_ABSTRACT,
        "group": "营运能力",
        "field": "应收账款周转率",
        "type": TYPE_TURNOVER_TIMES,
    },
    "总资产周转率": {
        "aliases": ["总资产周转率"],
        "source": SRC_ABSTRACT,
        "group": "营运能力",
        "field": "总资产周转率",
        "type": TYPE_TURNOVER_TIMES,
    },
    "存货周转天数": {
        "aliases": ["存货周转天数"],
        "source": SRC_ABSTRACT,
        "group": "营运能力",
        "field": "存货周转天数",
        "type": TYPE_TURNOVER_DAYS,
    },
}

# ---- 别名反查表 ----
def _build_alias_index():
    idx = {}
    for canonical, spec in METRIC_REGISTRY.items():
        idx[canonical] = canonical
        for alias in spec.get("aliases", []):
            idx[alias] = canonical
    return idx

_ALIAS_INDEX = _build_alias_index()

def normalize_metric(name):
    if name is None:
        return None
    return _ALIAS_INDEX.get(name.strip(), name.strip())

def get_spec(metric):
    """返回该指标的注册信息，未注册时返回 None。"""
    return METRIC_REGISTRY.get(metric)

def all_canonical_names():
    return list(METRIC_REGISTRY.keys())