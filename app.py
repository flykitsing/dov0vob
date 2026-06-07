import streamlit as st
import re
import os
import matplotlib
# 使用 Agg 後端以防止在無 GUI 的伺服器環境中執行 matplotlib 時出錯
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google import genai
import gspread
import requests
import pandas as pd
import random
from datetime import datetime

# ==========================================
# 1. 網頁初始化與 Session State 狀態管理
# ==========================================
st.set_page_config(page_title="新式學習工具", layout="wide")

# 初始化頁面導覽狀態
if "current_page" not in st.session_state:
    st.session_state.current_page = "menu"

# 初始化本地快取筆記本 (保證初次打開絕對有豐富內容，不會呈現空白！)
if "local_notes" not in st.session_state:
    st.session_state.local_notes = [
        {
            "subject": "數學", 
            "content": "勘根定理的前提：函數 $f(x)$ 必須在閉區間 $[a, b]$ 內連續，且 $f(a) \\cdot f(b) < 0$。若函數不連續（例如有分式斷點），則定理不一定成立！", 
            "time": "2026-06-01 10:30"
        },
        {
            "subject": "物理", 
            "content": "折射定律：由司乃耳定律 $n_1 \\sin\\theta_1 = n_2 \\sin\\theta_2$。光從空氣進入水中時，折射角小於入射角，光速變慢且波長變短，但頻率 $f$ 保持不變。", 
            "time": "2026-06-02 14:15"
        },
        {
            "subject": "地球科學", 
            "content": "大氣河流（Atmospheric Rivers）是大氣中極端水氣輸送的狹窄通道，其輸送的水氣量常等同於數條大河，是造成局部地區極端暴雨與洪災的主因。", 
            "time": "2026-06-03 09:00"
        },
        {
            "subject": "化學", 
            "content": "鉻酸鉀（$K_2CrO_4$）與銀離子（$Ag^+$）反應會生成磚紅色的鉻酸銀（$Ag_2CrO_4$）沉澱。此反應常用於莫耳法（Mohr method）滴定水中氯離子的終點指示。", 
            "time": "2026-06-04 16:45"
        },
        {
            "subject": "資訊科學", 
            "content": "快速排序（Quick Sort）與合併排序（Merge Sort）的平均時間複雜度均為 $O(n \\log n)$。然而快速排序在最差情況下會退化至 $O(n^2)$，且合併排序需要額外 $O(n)$ 的輔助空間。", 
            "time": "2026-06-05 11:20"
        }
    ]

# 歷史解題紀錄庫（與科目連動，供歷史複習出題）
if "history_questions" not in st.session_state:
    st.session_state.history_questions = {
        "數學": ["勘根定理的幾何意義與連續性函數關係？"],
        "物理": ["光從空氣斜射入水中的折射率推導？"],
        "地球科學": ["大氣河流（Atmospheric Rivers）的水氣輸送機制？"],
        "化學": ["氯化銀與鉻酸鉀沉澱時的顯色反應？"],
        "資訊科學": ["時間複雜度 O(n log n) 的排序演算法差異？"],
        "其他": []
    }

if "chem_q" not in st.session_state: st.session_state.chem_q = None
if "math_num" not in st.session_state: st.session_state.math_num = None
if "game_score" not in st.session_state: st.session_state.game_score = 0
if "review_score" not in st.session_state: st.session_state.review_score = 0

# ==========================================
# 2. 檢查並讀取 API 金鑰與雲端設定
# ==========================================
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")
spreadsheet_url = os.environ.get("SPREADSHEET_URL")

# 檢查最基礎的 Gemini API Key，若完全無 Key 則報錯
if not gemini_key:
    st.error("🔑 偵測不到關鍵的 GEMINI_API_KEY！請在 Streamlit 後台 Secrets 設定金鑰。")
    st.stop()

gemini_client = genai.Client(api_key=gemini_key)

# 具備防斷線與自動降級機制的 API 呼叫函式
def call_deepseek(prompt):
    if not deepseek_key:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=f"請作為學術審查員對此內容進行評估：\n\n{prompt}"
            )
            return response.text
        except Exception as e:
            return f"【審查模型降級失敗：{e}】"
            
    headers = {"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", json=data, headers=headers, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except Exception: 
        try:
            response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return response.text
        except:
            return "【審查中斷：連線超時】"

def call_groq(prompt):
    if not groq_key:
        try:
            response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return response.text
        except Exception as e:
            return f"【整合模型降級失敗：{e}】"
            
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except Exception: 
        try:
            response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return response.text
        except:
            return "【整合終審中斷：連線超時】"

# ==========================================
# 3. 🛡️ 雲端資料庫安全存取 (若失敗則自動不啟用，改用本地快取)
# ==========================================
cloud_active = False
notes_sheet_object = None

if spreadsheet_url:
    try:
        if "gspread_client" not in st.session_state:
            try:
                st.session_state.gspread_client = gspread.public()
            except:
                st.session_state.gspread_client = None
        
        gc = st.session_state.gspread_client
        if gc:
            sh = gc.open_by_url(spreadsheet_url)
            cloud_active = True
    except Exception:
        cloud_active = False

# ==========================================
# 4. 側邊欄：個人備忘錄即時讀取與快速儲存
# ==========================================
with st.sidebar:
    st.header("🧠 新式學習工具")
    if cloud_active:
        st.success("🟢 雲端同步系統已就緒")
    else:
        st.warning("🟡 目前運行於本地快取模式")
        
    subject = st.selectbox("當前專注科目", ["數學", "物理", "地球科學", "化學", "資訊科學", "其他"])
    
    notes_in_subject = []
    if cloud_active and spreadsheet_url:
        try:
            sh = st.session_state.gspread_client.open_by_url(spreadsheet_url)
            try:
                notes_sheet_object = sh.worksheet(subject)
            except gspread.exceptions.WorksheetNotFound:
                notes_sheet_object = sh.add_worksheet(title=subject, rows=500, cols=2)
                notes_sheet_object.update_cell(1, 1, "備忘內容")
                notes_sheet_object.update_cell(1, 2, "
