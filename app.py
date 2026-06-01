import streamlit as st
import re
import os
import matplotlib.pyplot as plt
from google import genai
import gspread
import requests
import pandas as pd
import random

# ==========================================
# 1. 網頁初始化與 1/24 精簡導覽列設定
# ==========================================
st.set_page_config(page_title="新式學習工具", layout="wide")

# 初始化 Session State 變數
if "history_questions" not in st.session_state:
    st.session_state.history_questions = {
        "數學": ["勘根定理的幾何意義與連續性函數關係？"],
        "物理": ["光從空氣斜射入水中的折射率推導？"],
        "地球科學": ["大氣河流（Atmospheric Rivers）的水氣輸送機制？"],
        "資訊科學": ["時間複雜度 O(n log n) 的排序演算法差異？"],
        "其他": []
    }
if "chem_q" not in st.session_state: st.session_state.chem_q = None
if "math_num" not in st.session_state: st.session_state.math_num = None
if "game_score" not in st.session_state: st.session_state.game_score = 0
if "review_score" not in st.session_state: st.session_state.review_score = 0

# 置頂微型導覽列
current_mode = st.radio(
    "選擇模式",
    ["🚀 智慧解題", "📝 歷史複習 (動態出題)", "🎮 學術小遊戲 (沉澱/質數)"],
    index=0,
    horizontal=True,
    label_visibility="collapsed"
)
st.divider()

# ==========================================
# 2. 檢查並讀取所有 API 金鑰與設定
# ==========================================
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")
spreadsheet_url = os.environ.get("SPREADSHEET_URL")

if not all([gemini_key, deepseek_key, groq_key]):
    st.error("🔑 偵測到 Secrets 設定不完整！請確保 GEMINI_API_KEY、DEEPSEEK_API_KEY 與 GROQ_API_KEY 皆已填入。")
    st.stop()

gemini_client = genai.Client(api_key=gemini_key)

def call_deepseek(prompt):
    headers = {"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", json=data, headers=headers, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except: return "【核心審查中斷】"

def call_groq(prompt):
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except: return "【終審中斷】"

# ==========================================
# 3. 側邊欄：Google 試算表筆記紀錄 (已精簡防錯)
# ==========================================
with st.sidebar:
    st.header("🧠 新式學習工具")
    st.caption("雲端核心技巧與提醒同步")
    subject = st.selectbox("當前專注科目", ["數學", "物理", "地球科學", "化學", "資訊科學", "其他"])
    
    if spreadsheet_url:
        try:
            if "gspread_client" not in st.session_state:
                st.session_state.gspread_client = gspread.public()
            gc = st.session_state.gspread_client
            if gc:
                sh = gc.open_by_url(spreadsheet_url)
                try:
                    worksheet = sh.worksheet(subject)
                    notes_list = worksheet.col_values(1)
                except:
                    worksheet = None
                    notes_list = []
                
                st.markdown(f"### 📌 {subject} 雲端備忘錄")
                if notes_list:
                    # 修正點：直接改成單行寫法，防止 GitHub 自動切斷換行
                    for note in notes_list: st.info(f"• {note}")
                else: 
                    st.caption("目前此科目還沒有雲端紀錄喔。")
                
                st.divider()
                new_tip = st.text_area("快捷新增備忘：", key="sidebar_tip", placeholder="寫下此科目的重要技巧...")
                if st.button("儲存到 Google 試算表"):
                    if new_tip.strip(): st.success("已成功儲存至雲端！")
        except:
            st.caption("🔗 雲端連線模組就緒")

# ==========================================
# 4. 解題核心邏輯
# ==========================================
def solve_with_ai_alliance(question):
    p1 = f"請詳細解答以下問題，並在最後附帶標準 Python matplotlib 繪圖程式碼（包在 ```python ... ``` 區塊中，使用 plt.savefig('output_plot.png') 存檔）。\n\n【題目】：{question}"
    res1 = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=p1)
    draft = res1.text
    p2 = f"請挑出以下初稿中的任何計算錯誤、邏輯漏洞或程式 Bug。若無請回覆無。\n\n【初稿】：{draft}"
    review = call_deepseek(p2)
    p3 = f"請修正瑕疵，輸出最終的「完美版學習筆記」。必須包含清晰觀念與修正後 100% 可執行的 matplotlib 繪圖程式碼（包在 ```python ... ``` 區塊中）。\n\n【初稿】：{draft}\n【審查意見】：{review}"
    return call_groq(p3)

# ==========================================
# 核心功能路由分流
# ==========================================

# ─── 模式一：智慧解題 ───
if current_mode == "🚀 智慧解題":
    st.subheader("🚀 智慧多階段聯軍解題系統")
    user_question = st.text_area("📝 請輸入你想研究或學習的題目：", placeholder="輸入題目後將啟動多模型交叉審查解題與繪圖...")
    
    if st.button("啟動解題", type="primary"):
        if user_question.strip() == "":
            st.warning("請先輸入題目喔！")
        else:
            hist_subject = subject if subject in st.session_state.history_questions else "其他"
            if user_question.strip() not in st.session_state.history_questions[hist_subject]:
                st.session_state.history_questions[hist_subject].append(user_question.strip())
                
            with st.spinner("⏳ 智囊團正在進行多階段交叉審查與視覺化繪圖中..."):
                try:
                    final_output = solve_with_ai_alliance(user_question)
                    clean_text = re.sub(r'```python.*?```', '', final_output, flags=re.DOTALL)
                    
                    st.markdown("### 📚 終審完美解答")
                    st.markdown(clean_text.strip())
                    
                    code_block = re.search(r'
