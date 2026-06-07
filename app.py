import streamlit as st
import re
import os
import requests
import random
from datetime import datetime

def safe_plot(code):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.figure()
        exec(code, globals())
        if os.path.exists('output_plot.png'):
            st.image('output_plot.png', use_container_width=True)
            os.remove('output_plot.png')
    except Exception as e:
        st.error(f"繪圖引擎異常：{e}")

def go_to_menu():
    st.session_state.current_page = "menu"

# ==========================================
# 1. 網頁初始化與 狀態管理
# ==========================================
st.set_page_config(page_title="新式學習工具", layout="wide")

if "current_page" not in st.session_state or st.session_state.current_page is None:
    st.session_state.current_page = "menu"

if "local_notes" not in st.session_state:
    st.session_state.local_notes = [
        {"subject": "數學", "content": "勘根定理的前提：函數 $f(x)$ 必須在閉區間 $[a, b]$ 內連續。", "time": "2026-06-01"},
        {"subject": "物理", "content": "折射定律：由司乃耳定律 $n_1 \\sin\\theta_1 = n_2 \\sin\\theta_2$。", "time": "2026-06-02"},
        {"subject": "地球科學", "content": "大氣河流是大氣中極端水氣輸送的狹窄通道。", "time": "2026-06-03"}
    ]

if "history_questions" not in st.session_state:
    st.session_state.history_questions = {
        "數學": ["勘根定理的幾何意義與連續性函數關係？"],
        "物理": ["光從空氣斜射入水中的折射率推導？"],
        "地球科學": ["大氣河流的水氣輸送機制？"],
        "化學": [], "資訊科學": [], "其他": []
    }

if "chem_q" not in st.session_state: st.session_state.chem_q = None
if "math_num" not in st.session_state: st.session_state.math_num = None
if "game_score" not in st.session_state: st.session_state.game_score = 0
if "review_score" not in st.session_state: st.session_state.review_score = 0

# ==========================================
# 2. 讀取 API 金鑰與模型呼叫
# ==========================================
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")

if not gemini_key:
    st.error("🔑 偵測不到關鍵的 GEMINI_API_KEY！請在 Streamlit Secrets 中設定。")
    st.stop()

from google import genai
gemini_client = genai.Client(api_key=gemini_key)

def call_gemini_backup(prompt_text):
    try:
        res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt_text)
        return res.text
    except:
        return "【模型運作失敗】"

def call_deepseek(prompt):
    if not deepseek_key:
        return call_gemini_backup(f"評估：\n\n{prompt}")
    try:
        api_url = "https://api.deepseek.com/v1/chat/completions"
        hd = {
            "Authorization": f"Bearer {deepseek_key}", 
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat", 
            "messages": [{"role": "user", "content": prompt}], 
            "temperature": 0.2
        }
        response = requests.post(url=api_url, json=payload, headers=hd, timeout=10)
        return response.json()['choices'][0]['message']['content']
    except:
        return call_gemini_backup(prompt)

def call_groq(prompt):
    if not groq_key:
        return call_gemini_backup(prompt)
    try:
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        hd = {
            "Authorization": f"Bearer {groq_key}", 
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile", 
            "messages": [{"role": "user", "content": prompt}], 
            "temperature": 0.2
        }
        response = requests.post(url=api_url, json=payload, headers=hd, timeout=10)
        return response.json()['choices'][0]['message']['content']
    except:
        return call_gemini_backup(prompt)

# ==========================================
# 3. 側邊欄面版
# ==========================================
with st.sidebar:
    st.header("🧠 新式學習工具")
    st.caption("🟢 本地安全快取模式")
    
    subject = st.selectbox("當前專注科目", ["數學", "物理", "地球科學", "化學", "資訊科學", "其他"])
    notes_in_subject = [n for n in st.session_state.local_notes if n["subject"] == subject]
        
    st.markdown(f"### 📌 {subject} 備忘錄")
    for item in notes_in_subject[-3:]:
        st.info(f"• {item['content']}")
        
    st.divider()
    
    user_note = st.text_area(label="快速新增筆記：", key="sb_note", placeholder="請在此輸入考點...", height=80)
    
    if st.button("儲存筆記"):
        if user_note.strip() != "":
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.local_notes.append({
                "subject": subject, 
                "content": user_note.strip(), 
                "time": now_str
            })
            st.success("🎉 儲存成功！")
            st.rerun()

# ==========================================
# 4. 主功能路由切換
# ==========================================
if st.session_state.current_page == "menu":
    st.title("🧠 新式學習工具")
    st.write("歡迎使用新式學科學習平台！請選擇功能模式：")
    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    with cols[0]:
        st.info("### 🚀 智慧解題")
        if st.button("進入解題系統", use_container_width=True, type="primary", key="go_solve"):
            st.session_state.current_page = "solve"
            st.rerun()
    with cols[1]:
        st.success("### 📝 歷史複習")
        if st.button("進入複習模式", use_container_width=True, type="primary", key="go_review"):
            st.session_state.current_page = "review"
            st.rerun()
    with cols[2]:
        st.warning("### 🎮 學術小遊戲")
        if st.button("進入遊戲競技場", use_container_width=True, type="primary", key="go_game"):
            st.session_state.current_page = "game"
            st.rerun()
    with cols[3]:
        st.error("### 📒 個人記事本")
        if st.button("打開個人記事本", use_container_width=True, type="primary", key="go_notebook"):
            st.session_state.current_page = "notebook"
            st.rerun()

elif st.session_state.current_page == "solve":
    st.button("⬅️ 回到主畫面", key="back_menu_solve", on_click=go_to_menu)
    st.subheader("🚀 智慧多階段聯軍解題系統")
    user_question = st.text_area("📝 請輸入你想研究或學習的題目：", key="solve_q_input")
    
    if st.button("啟動解題", type="primary", key="start_solve_btn"):
        if user_question.strip() != "":
            hist_subject = subject if subject in st.session_state.history_questions else "其他"
            st.session_state.history_questions[hist_subject].append(user_question.strip())
                
            with st.spinner("⏳ 智囊團正在深度交叉審查解題中..."):
                try:
                    p1 = f"請詳細解答問題，並附帶 Python 繪圖程式碼（包在 ```python ... ``` 區塊中，使用 plt.savefig('output_plot.png') 存檔）。\n\n【題目】：{user_question}"
                    draft = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=p1).text
                    review = call_deepseek(f"請挑出初稿中的錯誤或 Bug。若無回覆無。\n\n【初稿】：{draft}")
                    final_output = call_groq(f"請整合修正，輸出終審完美版筆記。必須包含繪圖程式碼（包在 ```python ... ``` 區塊中）。\n\n【初稿】：{draft}\n【審查意見】：{review}")
                    
                    clean_text = re.sub(r"
