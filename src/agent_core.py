"""
研报卫士 Agent 核心逻辑（无界面）。
对外暴露 agent_stream()，一个生成器，yield 事件字典：
  {"type": "tool_call", "name": ..., "args": {...}}
  {"type": "tool_result", "name": ..., "summary": "..."}
  {"type": "answer", "content": "..."}
界面层负责消费这些事件。
"""

import json
import akshare as ak
from dotenv import load_dotenv
from openai import OpenAI
import os

from metric_registry import METRIC_REGISTRY, normalize_metric, get_spec, SRC_INCOME, SRC_ABSTRACT

load_dotenv()
try:
    import streamlit as st
    API_KEY = st.secrets.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
except Exception:
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ---- 代码表（只加载一次）----
_code_table = None

def _ensure_code_table():
    global _code_table
    if _code_table is None:
        df = ak.stock_info_a_code_name()
        df["name_clean"] = df["name"].str.replace(r"\s+", "", regex=True)
        _code_table = df
    return _code_table

# ---- 工具：公司查询 ----
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

def tool_search_company(company_name):
    if not company_name:
        return {"error": "公司名为空"}
    table = _ensure_code_table()
    q = company_name.strip().replace(" ", "")

    m = table[table["name_clean"] == q]
    if not m.empty:
        return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "精确匹配"}

    core = _clean_name(q)
    if core and core != q:
        m = table[table["name_clean"] == core]
        if not m.empty:
            return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "去通用词后精确匹配"}

    m = table[table["name_clean"].str.contains(q, na=False, regex=False)]
    if m.empty and core:
        m = table[table["name_clean"].str.contains(core, na=False, regex=False)]
    if not m.empty:
        m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
        return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "包含匹配"}

    if core and len(core) >= 2:
        m = table[table["name_clean"].str.contains(core, na=False, regex=False)]
        if not m.empty:
            m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
            return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "品牌词匹配"}

    if core:
        for length in (4, 3, 2):
            for i in range(len(core) - length + 1):
                sub = core[i:i+length]
                m = table[table["name_clean"].str.contains(sub, na=False, regex=False)]
                if not m.empty:
                    m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
                    return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"],
                            "method": f"子串匹配（{sub}）"}
    return {"error": f"未找到公司：{company_name}"}

# ---- 工具：财报查询 ----
_income_cache = {}
_abstract_cache = {}

def _load_income(code):
    if code in _income_cache:
        return _income_cache[code]
    sina = ("sh" + code) if code.startswith(("6", "9")) else ("sz" + code)
    df = ak.stock_financial_report_sina(stock=sina, symbol="利润表")
    df["报告日_str"] = df["报告日"].astype(str).str.replace("-", "", regex=False)
    _income_cache[code] = df
    return df

def _load_abstract(code):
    if code in _abstract_cache:
        return _abstract_cache[code]
    df = ak.stock_financial_abstract(symbol=code)
    _abstract_cache[code] = df
    return df

def tool_get_financial(code, metric, year):
    spec = get_spec(normalize_metric(metric))
    if spec is None:
        return {"error": f"不支持的指标：{metric}",
                "hint": "调用 list_supported_metrics 查看支持的指标"}
    report_date = f"{year}1231"
    src = spec["source"]
    field = spec["field"]

    if src == SRC_INCOME:
        try:
            df = _load_income(code)
            row = df[df["报告日_str"] == report_date]
            if row.empty:
                return {"error": f"该期无数据：{report_date}"}
            val = float(row.iloc[0][field])
            return {"code": code, "metric": metric, "year": year,
                    "value": val, "unit": "元", "source": f"利润表/{field}"}
        except Exception as e:
            return {"error": f"利润表读取失败：{e}"}

    if src == SRC_ABSTRACT:
        group = spec["group"]
        try:
            df = _load_abstract(code)
            sub = df[(df["选项"] == group) & (df["指标"] == field)]
            if sub.empty:
                return {"error": f"财务摘要无该字段：{group}/{field}"}
            val = float(sub.iloc[0][report_date])
            mtype = spec["type"]
            unit = {"amount": "元", "ratio": "%", "per_share": "元/股"}.get(mtype, "?")
            return {"code": code, "metric": metric, "year": year,
                    "value": val, "unit": unit, "source": f"财务摘要/{group}/{field}"}
        except Exception as e:
            return {"error": f"财务摘要读取失败：{e}"}
    return {"error": f"未知数据源：{src}"}

def tool_list_supported_metrics():
    return {"metrics": list(METRIC_REGISTRY.keys())}

# ---- 工具 schema ----
TOOLS = [
    {"type": "function", "function": {
        "name": "search_company",
        "description": "根据公司中文名（简称或全称）查找 A 股股票代码。核查任何公司前必须先调用。",
        "parameters": {"type": "object", "properties": {
            "company_name": {"type": "string", "description": "公司中文名"}
        }, "required": ["company_name"]},
    }},
    {"type": "function", "function": {
        "name": "get_financial",
        "description": "查询某 A 股公司某年某财务指标的真实财报值。需先通过 search_company 拿代码。",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string"},
            "metric": {"type": "string"},
            "year": {"type": "integer"},
        }, "required": ["code", "metric", "year"]},
    }},
    {"type": "function", "function": {
        "name": "list_supported_metrics",
        "description": "列出支持核查的财务指标。不确定时调用。",
        "parameters": {"type": "object", "properties": {}},
    }},
]

def execute_tool(name, args):
    if name == "search_company":
        return tool_search_company(args.get("company_name"))
    if name == "get_financial":
        return tool_get_financial(args.get("code"), args.get("metric"), args.get("year"))
    if name == "list_supported_metrics":
        return tool_list_supported_metrics()
    return {"error": f"未知工具：{name}"}

# ---- 系统提示词 ----
SYSTEM_PROMPT = """你是"研报卫士"，一个专门核查金融研报的智能体。

【职责】
用户会给你研报片段、问题、或上传的文档。判断需要哪些信息，调用工具查证，给出核查结论。

【工具使用原则】
1. 不要凭记忆回答具体数字。任何"某公司某年某指标是多少"都必须调工具查证。
2. 标准核查流程：先 search_company 拿代码 → 再 get_financial 查询真实值 → 对比研报数字。
3. 不确定指标名 → 先 list_supported_metrics。
4. 工具报"不支持" → 诚实告知，不要编造。
5. 信息不足（缺公司/年份）→ 主动追问。
6. 公司不在 A 股（港股/美股/未上市）→ 直接说明，不要硬查。
7. 报告期未结束（如问 2026 年数据）→ 说明尚未披露。

【回答风格】
- 简洁专业
- 引用数据说明来源
- 核查到错误时给出：研报值 / 实际值 / 修改建议
- 无法核查时说清原因
"""

def agent_stream(user_input, history, extra_context=None):
    """
    生成器。每步 yield 一个事件。
    history 会被就地修改（累积多轮对话）。
    extra_context: 可选的额外上下文（如上传 PDF 的文字）
    """
    content = user_input
    if extra_context:
        content = f"{user_input}\n\n【附加上下文】\n{extra_context}"
    history.append({"role": "user", "content": content})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    for _ in range(10):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
            temperature=0,
        )
        msg = resp.choices[0].message

        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if not msg.tool_calls:
            history.append({"role": "assistant", "content": msg.content or ""})
            yield {"type": "answer", "content": msg.content or ""}
            return

        for tc in msg.tool_calls:
            fn = tc.function.name
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}

            yield {"type": "tool_call", "name": fn, "args": args}

            result = execute_tool(fn, args)

            s = json.dumps(result, ensure_ascii=False)
            summary = s[:150] + ("..." if len(s) > 150 else "")
            yield {"type": "tool_result", "name": fn, "summary": summary}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    yield {"type": "answer", "content": "（已达最大工具调用轮数）"}

def reset_code_table_cache():
    """如需强制重载代码表可调用。"""
    global _code_table
    _code_table = None