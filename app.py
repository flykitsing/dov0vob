import streamlit as st
import re
import os
import matplotlib.pyplot as plt
from google import genai
import requests

# 1. 網頁初始化設定
st.set_page_config(page_title="AI 聯軍智囊團", layout="wide")
st.title("🤝 AI 三巨頭聯軍解題工具 (Gemini x DeepSeek x Groq)")

# 2. 檢查並讀取三家 API 金鑰
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")

if not all([gemini_key, deepseek_key, groq_key]):
    st.error("🔑 偵測到 Secrets 設定不完整！請確保 GEMINI_API_KEY、DEEPSEEK_API_KEY 與 GROQ_API_KEY 皆已填入。")
    st.stop()

# 初始化 Gemini 客户端
gemini_client = genai.Client(api_key=gemini_key)

# 3. 定義外部 API (DeepSeek & Groq) 的呼叫函式 (使用標準 requests)
def call_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {deepseek_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat", # 或是 deepseek-reasoner (R1) 視你帳號额度而定
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    response = requests.post("https://api.deepseek.com/v1/chat/completions", json=data, headers=headers, timeout=30)
    return response.json()['choices'][0]['message']['content']

def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile", # 採用 Groq 目前最主力的高規格開源模型
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=30)
    return response.json()['choices'][0]['message']['content']

# 4. 聯軍大腦協同流程
def solve_with_ai_alliance(question):
    # ─── 階段 一：Gemini 2.5 Flash 撰寫初稿 ───
    prompt_stage1 = f"你現在是邏輯與程式能力極強的 AI 學習導師。請詳細解答以下問題，並在最後附帶標準 Python matplotlib 繪圖程式碼（包在 ```python ... ``` 區塊中，使用 plt.savefig('output_plot.png') 存檔）。\n\n【題目】：{question}"
    response_stage1 = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_stage1)
    draft_answer = response_stage1.text
    
    # ─── 階段 二：DeepSeek 強大邏輯進行深度審查 ───
    prompt_stage2 = f"你現在是極度嚴苛的學術論文審查員。請仔細閱讀以下初稿解答與繪圖程式碼，挑出任何計算錯誤、邏輯漏洞、定義不嚴謹或程式 Bug。若無請回覆無。\n\n【初稿】：{draft_answer}"
    review_feedback = call_deepseek(prompt_stage2)
    
    # ─── 階段 三：Groq (Llama 3) 高速進行結晶整合 ───
    prompt_stage3 = f"請看過「初稿內容」與「審查意見」後，修正所有瑕疵，輸出最終的「完美版學習筆記」。必須包含清晰的觀念解析與修正後 100% 可執行的 matplotlib 繪圖程式碼（包在 ```python ... ``` 區塊中）。\n\n【初稿】：{draft_answer}\n【審查意見】：{review_feedback}"
    final_combined = call_groq(prompt_stage3)
    
    return final_combined

# 5. 前端使用者介面
user_question = st.text_area("📝 請輸入你想研究或學習的題目：", placeholder="讓三巨頭聯軍幫你深度解題...")

if st.button("🚀 啟動聯軍解題", type="primary"):
    if user_question.strip() == "":
        st.warning("請先輸入題目喔！")
    else:
        with st.spinner("⏳ 🤖 Gemini 正在打底 ➔ 🧠 DeepSeek 正在嚴格挑錯 ➔ ⚡ Groq 正在高速終審..."):
            try:
                # 執行聯軍運算
                final_output = solve_with_ai_alliance(user_question)
                
                # 濾掉程式碼，單獨渲染文字
                clean_text = re.sub(r'```python.*?```', '', final_output, flags=re.DOTALL)
                st.markdown("### 📚 聯軍終審完美解答")
                st.markdown(clean_text.strip())
                
                # 抓取 Python 程式碼由本機執行畫圖
                code_block = re.search(r'```python(.*?)```', final_output, re.DOTALL)
                if code_block:
                    code = code_block.group(1).strip()
                    plt.figure() # 重置畫布
                    exec(code, globals())
                    
                    if os.path.exists('output_plot.png'):
                        st.markdown("### 📊 觀念視覺化圖形")
                        st.image('output_plot.png', use_container_width=True)
                        os.remove('output_plot.png')
            except Exception as e:
                st.error(f"聯軍運作時發生衝突錯誤：{e}")
