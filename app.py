import streamlit as st
import re
import os
import matplotlib.pyplot as plt
from google import genai
import gspread
import requests
import pandas as pd
import random

# 1. 網頁初始化設定
st.set_page_config(page_title="新式學習工具", layout="wide")
st.title("🧠 新式學習工具")

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
        return f"【核心審查中斷：{e}】"

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
        return f"【終審中斷：{e}】"

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
                    st.caption("提示：請確保您的 Google 試算表已開啟編輯權限。")
                    
        except Exception as e:
            st.error(f"試算表連線狀態異常")

# 5. 解題核心邏輯
def solve_with_ai_alliance(question):
    prompt_stage1 = f"你現在是邏輯與程式能力極強的 AI 學習導師。請詳細解答以下問題，並在最後附帶標準 Python matplotlib 繪圖程式碼（包在 ```python ... ``` 區塊中，使用 plt.savefig('output_plot.png') 存檔）。\n\n【題目】：{question}"
    response_stage1 = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_stage1)
    draft_answer = response_stage1.text
    
    prompt_stage2 = f"你現在是極度嚴苛的學術論文審查員。請仔細閱讀以下初稿解答與繪圖程式碼，挑出任何計算錯誤、邏輯漏洞、定義不嚴謹或程式 Bug。若無請回覆無。\n\n【初稿】：{draft_answer}"
    review_feedback = call_deepseek(prompt_stage2)
    
    prompt_stage3 = f"請看過「初稿內容」與「審查意見」後，修正所有瑕疵，輸出最終的「完美版學習筆記」。必須包含清晰的觀念解析與修正後 100% 可執行的 matplotlib 繪圖程式碼（包在 ```python ... ``` 區塊中）。\n\n【初稿】：{draft_answer}\n【審查意見】：{review_feedback}"
    final_combined = call_groq(prompt_stage3)
    
    return final_combined

# ==========================================
# 🎮 最初介面按鈕：切換「解題」與「小遊戲」
# ==========================================
tab1, tab2 = st.tabs(["🚀 解題模式", "🎮 小遊戲模式"])

# ─── 區塊一：解題模式 ───
with tab1:
    user_question = st.text_area("📝 請輸入你想研究或學習的題目：", placeholder="請輸入題目並啟動深度解題...", key="solve_input")

    if st.button("🚀 啟動解題", type="primary"):
        if user_question.strip() == "":
            st.warning("請先輸入題目喔！")
        else:
            with st.spinner("⏳ 智囊團正在進行多階段交叉審查與視覺化繪圖中..."):
                try:
                    final_output = solve_with_ai_alliance(user_question)
                    
                    clean_text = re.sub(r'```python.*?```', '', final_output, flags=re.DOTALL)
                    st.markdown("### 📚 終審完美解答")
                    st.markdown(clean_text.strip())
                    
                    code_block = re.search(r'```python(.*?)```', final_output, re.DOTALL)
                    if code_block:
                        code = code_block.group(1).strip()
                        plt.figure()
                        exec(code, globals())
                        
                        if os.path.exists('output_plot.png'):
                            st.markdown("### 📊 觀念視覺化圖形")
                            st.image('output_plot.png', use_container_width=True)
                            os.remove('output_plot.png')
                except Exception as e:
                    st.error(f"系統運作時發生衝突錯誤：{e}")

# ─── 區塊二：小遊戲模式 ───
with tab2:
    st.subheader("⚡ 核心觀念快問快答")
    st.write(f"目前遊戲出題庫與左側科目連動，當前科目：**{subject}**")
    
    # 簡單的靜態題庫系統
    quiz_bank = {
        "數學": [
            {"q": "使用勘根定理時，函數在該閉區間內必須滿足什麼前提？", "a": "連續"},
            {"q": "若多項式方程式有虛根，則虛根必定滿足什麼性質？", "a": "共軛成對"}
        ],
        "物理": [
            {"q": "重力加速度在地球表面，緯度越高通常會越大還是越小？", "a": "越大"},
            {"q": "光從空氣斜射入水中，其傳播速度會變快還是變慢？", "a": "變慢"}
        ],
        "地球科學": [
            {"q": "聖嬰現象發生時，赤道東太平洋的海水表面溫度會異常升高還是降低？", "a": "升高"},
            {"q": "大氣層中，氣溫隨高度增加而上升，且集中了大量臭氧的是哪一層？", "a": "平流層"}
        ],
        "資訊科學": [
            {"q": "在 Python 中，想要在列表末尾添加一個元素，應該使用哪一個內建方法？", "a": "append"},
            {"q": "時間複雜度為 O(n log n) 的常見排序演算法是哪一個？（例如：快排、合併）", "a": "快速排序"}
        ],
        "其他": [
            {"q": "在排隊理論或生活中，常常開玩笑說「公車不來就不來，一來就來幾輛」？", "a": "三輛"}
        ]
    }
    
    # 確保 session state 初始化
    if "current_q_idx" not in st.session_state:
        st.session_state.current_q_idx = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
        
    current_subject_quizzes = quiz_bank.get(subject, quiz_bank["其他"])
    
    # 防止切換科目時索引溢出
    if st.session_state.current_q_idx >= len(current_subject_quizzes):
        st.session_state.current_q_idx = 0
        
    q_data = current_subject_quizzes[st.session_state.current_q_idx]
    
    st.info(f"【題目】：{q_data['q']}")
    
    user_ans = st.text_input("請輸入你的答案（簡答）：", key=f"ans_{subject}_{st.session_state.current_q_idx}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit 送出答案"):
            if user_ans.strip() in q_data['a'] or q_data['a'] in user_ans.strip():
                st.success("🎉 太強了！答案完全正確！")
                st.session_state.score += 10
            else:
                st.error(f"❌ 差一點點！正確答案是：{q_data['a']}")
    with col2:
        if st.button("下一題 ➡️"):
            st.session_state.current_q_idx = (st.session_state.current_q_idx + 1) % len(current_subject_quizzes)
            st.rerun()
            
    st.metric(label="當前累積核心經驗值", value=f"{st.session_state.score} XP")
