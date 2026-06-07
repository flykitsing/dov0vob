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

if "current_page" not in st.session_state or st.session_state.current_page is None:
    st.session_state.current_page = "menu"

# 純本地記憶體快取，免去登入與雲端資料庫綁定
if "local_notes" not in st.session_state:
    st.session_state.local_notes = [
        {"subject": "數學", "content": "勘根定理的前提：函數 $f(x)$ 必須在閉區間 $[a, b]$ 內連續，且 $f(a) \\cdot f(b) < 0$。", "time": "2026-06-01 10:30"},
        {"subject": "物理", "content": "折射定律：由司乃耳定律 $n_1 \\sin\\theta_1 = n_2 \\sin\\theta_2$。", "time": "2026-06-02 14:15"},
        {"subject": "地球科學", "content": "大氣河流是大氣中極端水氣輸送的狹窄通道。", "time": "2026-06-03 09:00"}
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
# 2. 讀取 AI API 金鑰
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
# 3. 側邊欄：個人備忘錄 (已移除登入與同步)
# ==========================================
with st.sidebar:
    st.header("🧠 新式學習工具")
    st.caption("🟢 本地安全快取模式已啟動")
    
    subject = st.selectbox("當前專注科目", ["數學", "物理", "地球科學", "化學", "資訊科學", "其他"])
    
    # 直接篩選本地快取的筆記
    notes_in_subject = [n for n in st.session_state.local_notes if n["subject"] == subject]
        
    st.markdown(f"### 📌 {subject} 備忘錄")
    for item in notes_in_subject[-3:]:
        st.info(f"• {item['content']}")
        
    st.divider()
    
    txt_holder = "請在此輸入考點或筆記..."
    user_note = st.text_area(label="快速新增筆記：", key="sb_note", placeholder=txt_holder, height=80)
    
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
# 4. 主網頁功能路由
# ==========================================
if st.session_state.current_page == "menu":
    st.title("🧠 新式學習工具")
    st.write("歡迎使用新式學科學習平台！請選擇功能模式：")
    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns(4)
    col1 = cols[0]
    col2 = cols[1]
    col3 = cols[2]
    col4 = cols[3]
    
    with col1:
        st.info("### 🚀 智慧解題")
        if st.button("進入解題系統", use_container_width=True, type="primary", key="go_solve"):
            st.session_state.current_page = "solve"
            st.rerun()
    with col2:
        st.success("### 📝 歷史複習")
        if st.button("進入複習模式", use_container_width=True, type="primary", key="go_review"):
            st.session_state.current_page = "review"
            st.rerun()
    with col3:
        st.warning("### 🎮 學術小遊戲")
        if st.button("進入遊戲競技場", use_container_width=True, type="primary", key="go_game"):
            st.session_state.current_page = "game"
            st.rerun()
    with col4:
        st.error("### 📒 個人記事本")
        if st.button("打開個人記事本", use_container_width=True, type="primary", key="go_notebook"):
            st.session_state.current_page = "notebook"
            st.rerun()

elif st.session_state.current_page == "solve":
    if st.button("⬅️ 回到主畫面", key="back_menu_solve"):
        st.session_state.current_page = "menu"
        st.rerun()
        
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
                    
                    clean_text = re.sub(r"```python.*?```", "", final_output, flags=re.DOTALL)
                    st.markdown("### 📚 終審完美解答")
                    st.markdown(clean_text.strip())
                    
                    code_block = re.search(r"```python(.*?)```", final_output, flags=re.DOTALL)
                    if code_block:
                        st.markdown("### 📊 觀念視覺化圖形")
                        safe_plot(code_block.group(1).strip())
                except Exception as e:
                    st.error(f"系統運作時發生衝突錯誤：{e}")

elif st.session_state.current_page == "review":
    if st.button("⬅️ 回到主畫面", key="back_menu_review"):
        st.session_state.current_page = "menu"
        st.rerun()
    st.subheader("📝 錯題與歷史觀念動態複習")
    current_pool = st.session_state.history_questions.get(subject, [])
    if not current_pool:
        st.info(f"💡 目前「{subject}」還沒有歷史解題紀錄喔！")
    else:
        review_q = current_pool[0]
        st.warning(f"【歷史複習主題】：{review_q}")
        ans_input = st.text_area("請簡述這個觀念的核心關鍵：", key="review_ans_input")
        if st.button("提交複習答案並由 AI 評分", key="submit_review_btn"):
            with st.spinner("🔍 評分中..."):
                score_feedback = call_deepseek(f"真實題目：{review_q}。學生回答：{ans_input}。請在3行內給予0~100評分並給予建議。")
                st.success("📊 複習審查回饋：")
                st.write(score_feedback)

elif st.session_state.current_page == "game":
    if st.button("⬅️ 回到主畫面", key="back_menu_game"):
        st.session_state.current_page
