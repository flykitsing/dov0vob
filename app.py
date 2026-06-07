import streamlit as st
import re
import os
import requests
import random
from datetime import datetime

# 將 matplotlib 延後到需要繪圖時才匯入，防止網頁初始化直接崩潰
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

# ==========================================
# 1. 網頁初始化與 Session State 狀態管理
# ==========================================
st.set_page_config(page_title="新式學習工具", layout="wide")

if "current_page" not in st.session_state:
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
# 2. 讀取 API 金鑰
# ==========================================
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")
spreadsheet_url = os.environ.get("SPREADSHEET_URL")

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
        headers = {"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"}
        data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        response = requests.post("https://api.deepseek.com/v1/chat/completions", json=data, headers=headers, timeout=10)
        return response.json()['choices'][0]['message']['content']
    except:
        return call_gemini_backup(prompt)

def call_groq(prompt):
    if not groq_key:
        return call_gemini_backup(prompt)
    try:
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        response = requests.post("
