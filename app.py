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
                model='
