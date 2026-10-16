import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    print("❌ 没有读到 DEEPSEEK_API_KEY")
    print("请检查：")
    print("1. 项目根目录下是否有 .env 文件")
    print("2. .env 里是否写着 DEEPSEEK_API_KEY=sk-...")
    print("3. 运行这个脚本时，工作目录是否是项目根目录")
else:
    print("✅ 成功读到 DEEPSEEK_API_KEY")
    print("密钥前 6 位：", api_key[:6])
    print("密钥长度：", len(api_key))