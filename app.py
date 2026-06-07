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
        api_url = "https://api.deepseek.com/v1/chat/completions"
        hd = {"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"}
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
        hd = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
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
# 3. 雲端資料庫安全存取
# ==========================================
cloud_active = False
notes_sheet_object = None

if spreadsheet_url:
    try:
        import gspread
        if "gspread_client" not in st.session_state or st.session_state.gspread_client is None:
            st.session_state.gspread_client = gspread.public()
        if st.session_state.gspread_client:
            sh = st.session_state.gspread_client.open_by_url(spreadsheet_url)
            cloud_active = True
    except:
        cloud_active = False

# ==========================================
# 4. 側邊欄：個人備忘錄
# ==========================================
with st.sidebar:
    st.header("🧠 新式學習工具")
    subject = st.selectbox("當前專注科目", ["數學", "物理", "地球科學", "化學", "資訊科學", "其他"])
    notes_in_subject = []
    
    if cloud_active and spreadsheet_url:
        try:
            sh = st.session_state.gspread_client.open_by_url(spreadsheet_url)
            try:
                notes_sheet_object = sh.worksheet(subject)
            except:
                notes_sheet_object = sh.add_worksheet(title=subject, rows=500, cols=2)
                notes_sheet_object.update_cell(1, 1, "備忘內容")
                notes_sheet_object.update_cell(1, 2, "建立時間")
            all_rows = notes_sheet_object.get_all_values()
            if len(all_rows) > 1:
                notes_in_subject = [{"row_idx": idx + 2, "content": r[0], "time": r[1]} for idx, r in enumerate(all_rows[1:]) if r[0].strip() != ""]
        except:
            pass
            
    if not notes_in_subject:
        notes_in_subject = [{"row_idx": idx, "content": n["content"], "time": n["time"]} for idx, n in enumerate(st.session_state.local_notes) if n["subject"] == subject]
        
    st.markdown(f"### 📌 {subject} 備忘錄")
    for item in notes_in_subject[-3:]:
        st.info(f"• {item['content']}")
        
    st.divider()
    
    # 這裡就是剛才被截斷的災情發生處！這次徹底拆解成極短行，確保絕對不卡死
    txt_holder = "請在此輸入..."
    user_note = st.text_area(label="快速新增筆記：", key="sb_note", placeholder=txt_holder, height=80)
    
    if st.button("儲存筆記"):
        if user_note.strip() != "":
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.local_notes.append({"subject": subject, "content": user_note.strip(), "time": now_str})
            if cloud_active and notes_sheet_object is not None:
                try: 
                    notes_sheet_object.append_row([user_note.strip(), now_str])
                except: 
                    pass
            st.success("🎉 儲存成功！")
            st.rerun()

# ==========================================
# 5. 主網頁功能路由
#
