"""
研报卫士 Agent v0.1
一个最小可用的对话式智能体。

特点：
- LLM 自主决定何时调用工具、调哪个工具
- 有对话记忆，支持追问
- 工具集：公司查询 / 财报查询 / 指标列表
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import akshare as ak

from metric_registry import (
    METRIC_REGISTRY, normalize_metric, get_spec,
    SRC_INCOME, SRC_ABSTRACT,
)

# ============ 初始化 ============
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("未读取到 DEEPSEEK_API_KEY")

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

print("加载 A 股代码表 ...")
_code_table = ak.stock_info_a_code_name()
_code_table["name_clean"] = _code_table["name"].str.replace(r"\s+", "", regex=True)
print(f"已加载 {len(_code_table)} 家公司\n")

# ============ 工具 1：公司名 → 股票代码 ============
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
    q = company_name.strip().replace(" ", "")

    m = _code_table[_code_table["name_clean"] == q]
    if not m.empty:
        return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "精确匹配"}

    core = _clean_name(q)
    if core and core != q:
        m = _code_table[_code_table["name_clean"] == core]
        if not m.empty:
            return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "去通用词后精确匹配"}

    m = _code_table[_code_table["name_clean"].str.contains(q, na=False, regex=False)]
    if m.empty and core:
        m = _code_table[_code_table["name_clean"].str.contains(core, na=False, regex=False)]
    if not m.empty:
        m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
        return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "包含匹配"}

    if core and len(core) >= 2:
        m = _code_table[_code_table["name_clean"].str.contains(core, na=False, regex=False)]
        if not m.empty:
            m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
            return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"], "method": "品牌词匹配"}

    if core:
        for length in (4, 3, 2):
            for i in range(len(core) - length + 1):
                sub = core[i:i+length]
                m = _code_table[_code_table["name_clean"].str.contains(sub, na=False, regex=False)]
                if not m.empty:
                    m = m.assign(_len=m["name_clean"].str.len()).sort_values("_len")
                    return {"code": m.iloc[0]["code"], "name": m.iloc[0]["name"],
                            "method": f"子串匹配（{sub}）"}

    return {"error": f"未找到公司：{company_name}"}

# ============ 工具 2：查财报 ============
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
            unit = "%" if spec["type"] == "ratio" else (
                "元" if spec["type"] == "amount" else
                "元/股" if spec["type"] == "per_share" else
                "次/天" if "turnover" in spec["type"] else "?"
            )
            return {"code": code, "metric": metric, "year": year,
                    "value": val, "unit": unit, "source": f"财务摘要/{group}/{field}"}
        except Exception as e:
            return {"error": f"财务摘要读取失败：{e}"}

    return {"error": f"未知数据源：{src}"}

# ============ 工具 3：列出支持的指标 ============
def tool_list_supported_metrics():
    return {"metrics": list(METRIC_REGISTRY.keys())}

# ============ 工具注册（OpenAI function calling schema）============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_company",
            "description": "根据公司中文名（简称或全称）查找 A 股股票代码。核查任何公司前必须先调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "公司中文名，如'伊利股份'或'内蒙古伊利实业集团股份有限公司'",
                    }
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial",
            "description": "查询某 A 股公司某年某财务指标的真实财报值。需要先通过 search_company 拿到股票代码。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "6 位股票代码，如 '600887'"},
                    "metric": {"type": "string", "description": "指标名，如 '营业收入'、'归母净利润'、'毛利率'"},
                    "year": {"type": "integer", "description": "报告期年份，如 2025"},
                },
                "required": ["code", "metric", "year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_supported_metrics",
            "description": "列出当前支持核查的所有财务指标。当不确定某指标是否支持时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

def execute_tool(name, args):
    if name == "search_company":
        return tool_search_company(args.get("company_name"))
    if name == "get_financial":
        return tool_get_financial(args.get("code"), args.get("metric"), args.get("year"))
    if name == "list_supported_metrics":
        return tool_list_supported_metrics()
    return {"error": f"未知工具：{name}"}

# ============ 系统提示词 ============
SYSTEM_PROMPT = """你是"研报卫士"，一个专门核查金融研报的智能体。

【职责】
用户会给你研报片段或问题。你要判断需要哪些信息，调用工具查证，然后给出核查结论。

【工具使用原则】
1. 不要凭记忆回答具体数字。任何"某公司某年某指标是多少"都必须调工具查证。
2. 核查流程：
   - 先 search_company 拿到股票代码
   - 再 get_financial 查询该指标的真实值
   - 对比研报里的数字，判断是否有误
3. 不确定指标名 → 先 list_supported_metrics 看支持列表
4. 工具报"不支持" → 诚实告诉用户，不要编造
5. 信息不足（缺公司名/年份）→ 主动追问用户

【回答风格】
- 简洁专业，不啰嗦
- 引用数据时说明来源（如"财报显示伊利 2025 年营业收入为 X"）
- 核查到错误时，给出：错误值 / 正确值 / 修改建议
- 无法核查时，说清楚原因

【示例对话】
用户：伊利股份2025年营业收入是1156亿，对吗？
你：（应该先调 search_company("伊利股份") → 再调 get_financial("600887", "营业收入", 2025)）
    然后基于结果回答："研报数字 1156 亿，财报实际值为 1156.36 亿，一致。"
"""

# ============ Agent Loop ============
MAX_TOOL_ROUNDS = 10   # 防止无限循环

def agent_loop(user_input, history):
    """一轮对话。history 是累积的对话历史，会被修改。"""
    history.append({"role": "user", "content": user_input})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
            temperature=0,
        )
        msg = resp.choices[0].message

        # 组装 assistant 消息
        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        # 无工具调用 → 结束这一轮
        if not msg.tool_calls:
            history.append({"role": "assistant", "content": msg.content or ""})
            return msg.content or ""

        # 执行工具
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}

            print(f"  🔧 {fn_name}({json.dumps(args, ensure_ascii=False)})")
            result = execute_tool(fn_name, args)
            preview = json.dumps(result, ensure_ascii=False)
            if len(preview) > 120:
                preview = preview[:120] + "..."
            print(f"     ↳ {preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return "（已达到最大工具调用轮数，中止）"

# ============ 主循环 ============
if __name__ == "__main__":
    print("=" * 60)
    print("研报卫士 Agent v0.1")
    print("=" * 60)
    print("直接提问即可。示例：")
    print("  · 伊利股份2025年营业收入是多少？")
    print("  · 伊利股份2025年营业收入1156亿，对吗？")
    print("  · 你支持核查哪些指标？")
    print("输入 exit 退出。")
    print("=" * 60)

    history = []
    while True:
        try:
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q", "退出"):
            print("再见。")
            break

        print()
        try:
            answer = agent_loop(user_input, history)
            print(f"\n卫士> {answer}")
        except Exception as e:
            print(f"\n[错误] {type(e).__name__}: {e}")