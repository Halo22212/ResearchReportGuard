import os
import io
import fitz
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

from agent_core import agent_stream

# ============ 初始化 ============
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

if not os.getenv("DEEPSEEK_API_KEY"):
    st.error("未读取到 DEEPSEEK_API_KEY，请检查 .env 文件。")
    st.stop()

st.set_page_config(page_title="研报卫士", page_icon="🛡️", layout="wide")

# ============ 侧边栏：PDF 上传 ============
with st.sidebar:
    st.header("📄 上传研报（可选）")
    uploaded = st.file_uploader("选择 PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded is not None:
        try:
            doc = fitz.open(stream=uploaded.getvalue(), filetype="pdf")
            pages_text = []
            for i in range(doc.page_count):
                t = doc[i].get_text("text").strip()
                if t:
                    pages_text.append(f"[第 {i+1} 页]\n{t}")
            doc.close()
            full_text = "\n\n".join(pages_text)
            st.session_state["pdf_text"] = full_text
            st.success(f"已加载：{uploaded.name}（{len(pages_text)} 页）")
            st.caption(f"约 {len(full_text)} 字，已加入对话上下文。")
        except Exception as e:
            st.error(f"PDF 解析失败：{e}")

    if st.session_state.get("pdf_text"):
        if st.button("清除已上传 PDF"):
            st.session_state.pop("pdf_text", None)
            st.rerun()

    st.markdown("---")
    st.markdown("**我可以帮你：**")
    st.markdown("- 核查某公司某年某指标")
    st.markdown("- 分析你上传的研报有无数字错误")
    st.markdown("- 解释核查依据")
    st.markdown("**范围**：A 股上市公司公开财报")

    if st.button("清空对话"):
        st.session_state["messages"] = []
        st.session_state["agent_history"] = []
        st.rerun()

# ============ 主区域 ============
st.title("🛡️ 研报卫士")
st.caption("上传研报 或 直接提问，我会自动调取财报核查，给出结论、证据和修改建议。")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "agent_history" not in st.session_state:
    st.session_state["agent_history"] = []

# 欢迎语
if not st.session_state["messages"]:
    with st.chat_message("assistant"):
        st.markdown(
            "你好，我是研报卫士。你可以：\n\n"
            "- 直接问我：**伊利股份2025年营业收入是多少？**\n"
            "- 让我核查：**伊利股份2025年营收1156亿，对吗？**\n"
            "- 上传一份研报 PDF，然后问我**这份研报有没有问题**\n\n"
            "我会自己决定查哪些数据，并给出依据。"
        )

# 渲染历史消息
for m in st.session_state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 输入
user_input = st.chat_input("输入你的问题...")

if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status = st.status("正在思考...", expanded=True)
        answer = ""
        extra = st.session_state.get("pdf_text")

        try:
            for event in agent_stream(
                user_input,
                st.session_state["agent_history"],
                extra_context=extra,
            ):
                if event["type"] == "tool_call":
                    args_str = ", ".join(f"{k}={v}" for k, v in event["args"].items())
                    status.write(f"🔧 调用 `{event['name']}({args_str})`")
                elif event["type"] == "tool_result":
                    status.write(f"　↳ {event['summary']}")
                elif event["type"] == "answer":
                    answer = event["content"]

            status.update(label="✅ 完成", state="complete", expanded=False)
            st.markdown(answer)
        except Exception as e:
            status.update(label="❌ 出错", state="error")
            st.error(f"出错：{type(e).__name__}: {e}")
            answer = f"（出错：{e}）"

    st.session_state["messages"].append({"role": "assistant", "content": answer})