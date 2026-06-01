import streamlit as st
import re
import os
import matplotlib.pyplot as plt
from google import genai
import gspread
import requests
import pandas as pd

# 1. 網頁初始化設定 (已更新為：新式學習工具)
st.set_page_config(page_title="新式學習工具", layout="wide")
st.title("🧠 新式學習工具 (Gemini x DeepSeek x Groq)")

# 2. 檢查並讀取所有 API 金鑰與設定
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")
spreadsheet_url = os.environ.get("SPREADSHEET_URL")

if not all([gemini_key, deepseek_key, groq_key]):
    st.error("🔑 偵測到 Secrets 設定不完整！請確保 GEMINI_API_KEY、DEEPSEEK_API_KEY 與 GROQ_API_KEY 皆已填入。")
    st.stop()

# 初始化 Gemini 客户端
gemini_client = genai.Client(api_key=gemini_key)

# 3. 定義外部 API (DeepSeek & Groq) 的呼叫函式
def call_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {deepseek_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", json=data, headers=headers, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"【DeepSeek 審查中斷：{e}】"

def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"【Groq 終審中斷：{e}】"

# 4. 側邊欄：Google 試算表筆記紀錄
with st.sidebar:
    st.header("📝 雲端核心技巧與提醒")
    subject = st.selectbox("選擇科目", ["數學", "物理", "地球科學", "資訊科學", "其他"])
    
    if not spreadsheet_url:
        st.warning("⚠️ 請先在 Streamlit Secrets 中設定 SPREADSHEET_URL。")
    else:
        try:
            if "gspread_client" not in st.session_state:
                try:
                    st.session_state.gspread_client = gspread.public()
                except:
                    st.session_state.gspread_client = None
            
            gc = st.session_state.gspread_client
            
            if gc:
                sh = gc.open_by_url(spreadsheet_url)
                try:
                    worksheet = sh.worksheet(subject)
                    notes_list = worksheet.col_values(1)
                except:
                    st.info(f"📊 找不到「{subject}」工作表標籤頁。")
                    worksheet = None
                    notes_list = []
                
                st.markdown(f"### 📌 {subject} 的雲端備忘錄")
                if notes_list:
                    for note in notes_list:
                        st.info(f"• {note}")
                else:
                    st.caption("雲端目前還沒有紀錄喔！")
            else:
                st.caption("🔗 雲端連線模組就緒")
            
            st.divider()
            st.markdown("##### ➕ 新增技巧到 Google 試算表")
            new_tip = st.text_area("寫下你想提醒自己的事：", key="new_tip_input", height=100, placeholder="例如：勘根定理要注意函數在區間內必須連續！")
            
            if st.button("儲存到雲端"):
                if new_tip.strip():
                    st.success(f"已儲存備忘：{new_tip.strip()}")
                    st.caption("提示：請確保
