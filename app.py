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

# 初始化 Session State 變數，用於管理歷史紀錄與遊戲狀態
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

# 置頂微型導覽列 (約佔畫面的 1/24 高度)
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
    except: 
        return "【核心審查中斷】"

def call_groq(prompt):
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except: 
        return "【終審中斷】"

# ==========================================
# 3. 🎯 核心優化：Google 試算表筆記本功能 (雙向讀寫 + 自動建表防錯)
# ==========================================
worksheet_object = None  # 用於在主程式與側邊欄共用的試算表物件
notes_list = []          # 當前科目的備忘錄清單

with st.sidebar:
    st.header("🧠 新式學習工具")
    st.caption("雲端筆記本與提醒同步")
    subject = st.selectbox("當前專注科目", ["數學", "物理", "地球科學", "化學", "資訊科學", "其他"])
    
    if not spreadsheet_url:
        st.warning("⚠️ 請先在 Streamlit Secrets 中設定 SPREADSHEET_URL。")
    else:
        try:
            # 建立與 Google 試算表的連線 (匿名/公開編輯權限模式)
            if "gspread_client" not in st.session_state:
                try:
                    st.session_state.gspread_client = gspread.public()
                except Exception:
                    st.session_state.gspread_client = None
            
            gc = st.session_state.gspread_client
            
            if gc:
                # 打開試算表
                sh = gc.open_by_url(spreadsheet_url)
                
                # 嘗試讀取當前科目的工作表 (Worksheet)
                try:
                    worksheet_object = sh.worksheet(subject)
                    # 讀取第一欄的所有內容 (第 1 列通常是標題「技巧紀錄」)
                    all_values = worksheet_object.col_values(1)
                    notes_list = all_values[1:] if len(all_values) > 1 else []
                except gspread.exceptions.WorksheetNotFound:
                    # 💡 防呆機制：如果找不到該科目的工作表，就自動幫使用者創建一個！
                    st.info(f"📊 偵測到雲端無「{subject}」工作表，正在自動為您建立分頁...")
                    worksheet_object = sh.add_worksheet(title=subject, rows=100, cols=3)
                    # 寫入第一行首列作為標題欄
                    worksheet_object.update_cell(1, 1, "技巧紀錄")
                    notes_list = []
                except Exception as worksheet_err:
                    st.error("工作表讀取發生異常")
                    st.caption(f"錯誤細節: {worksheet_err}")
                
                # 呈現雲端備忘錄內容
                st.markdown(f"### 📌 {subject} 雲端備忘錄")
                if notes_list:
                    # 移除空白行並呈現
                    for note in notes_list:
                        if note.strip():
                            st.info(f"• {note}")
                else:
                    st.caption("目前此科目雲端上還沒有紀錄喔。在下方輸入框寫點東西並存入吧！")
                
                st.divider()
                
                # 新增技巧備忘至雲端
                new_tip = st.text_area("快捷新增備忘：", key="sidebar_tip", placeholder="例如：寫下重要考點或解題大招...")
                
                if st.button("儲存到 Google 試算表"):
                    if new_tip.strip() == "":
                        st.warning("請先輸入備忘內容！")
                    elif worksheet_object is not None:
                        with st.spinner("⏳ 正在將筆記同步寫入雲端..."):
                            try:
                                # 真正將資料寫入 Google Sheets 的最後一行 (Append Row)
                                worksheet_object.append_row([new_tip.strip()])
                                st.success("🎉 已成功儲存至 Google 試算表！")
                                # 自動重新整理，即時顯示最新儲存的筆記
                                st.rerun()
                            except Exception as write_err:
                                st.error("儲存失敗，請確認您的 Google 試算表右上角是否已開啟「知道連結的人均可編輯」權限。")
                                st.caption(f"錯誤細節: {write_err}")
            else:
                st.caption("🔗 雲端連線模組初始化中...")
        except Exception as conn_err:
            st.error("試算表連線狀態異常")
            st.caption(f"請確保 Secrets 的 SPREADSHEET_URL 為完整的試算表網址。錯誤訊息: {conn_err}")

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
# 5. 核心功能路由分流
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
                    
                    # 使用安全的三引號封裝正規表達式，徹底杜絕單引號斷行造成的字串未閉合錯誤
                    clean_text = re.sub(r"""```python.*?```""", "", final_output, flags=re.DOTALL)
                    
                    st.markdown("### 📚 終審完美解答")
                    st.markdown(clean_text.strip())
                    
                    code_block = re.search(r"""```python(.*?)```""", final_output, re.DOTALL)
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

# ─── 模式二：歷史複習 (動態出題) ───
elif current_mode == "📝 歷史複習 (動態出題)":
    st.subheader("📝 錯題與歷史觀念動態複習")
    st.write(f"目前正在加強複習的科目：**{subject}**")
    
    current_pool = st.session_state.history_questions.get(subject, [])
    
    if not current_pool:
        st.info(f"💡 目前「{subject}」還沒有歷史解題紀錄喔！你去解題模式問過的問題，會自動出現在這裡。")
    else:
        st.write("根據你之前問過的題目，AI 聯軍重新為你提煉出核心核心觀念快問：")
        review_q = current_pool[0]
        st.warning(f"【歷史複習主題】：{review_q}")
        
        st.write("👉 請在腦中或紙上試著推導並寫出該題目的核心解題關鍵。")
        ans_input = st.text_area("請簡述這個觀念的核心關鍵（例如公式、前提、或現象原因）：", key="review_ans")
        
        if st.button("提交複習答案並由 AI 評分"):
            if ans_input.strip():
                with st.spinner("🔍 正在調閱歷史檔案比對你的回答..."):
                    score_prompt = f"使用者先前問過這題：{review_q}。他現在的複習回答是：{ans_input}。請在 3 行內針對他的回答給予 0~100 的評分，並指出他有沒有抓到最核心的關鍵點。"
                    score_feedback = call_deepseek(score_prompt)
                    st.success("📊 複習審查回饋：")
                    st.write(score_feedback)
                    st.session_state.review_score += 20
                    st.metric("複習增長經驗值", f"{st.session_state.review_score} XP")

# ─── 模式三：學術小遊戲 (沉澱/質數) ───
elif current_mode == "🎮 學術小遊戲 (沉澱/質數)":
    st.subheader("🎮 學術終結者競技場")
    
    game_type = st.selectbox("請選擇你想挑戰的遊戲種類：", ["🧪 化學沉澱終結者", "🔢 數學質數分解王"])
    
    # ----- 遊戲 A：化學沉澱終結者 -----
    if game_type == "🧪 化學沉澱終結者":
        st.markdown("#### 🧪 化學沉澱與顏色對戰")
        st.caption("遊戲規則：系統會隨機混和兩種離子，請判斷它們是否會產生沉澱？若會沉澱，是什麼顏色？")
        
        chem_db = [
            {"ion1": "Ag⁺", "ion2": "Cl⁻", "precipitate": "是", "color": "白色"},
            {"ion1": "Ba²⁺", "ion2": "SO₄²⁻", "precipitate": "是", "color": "白色"},
            {"ion1": "Cu²⁺", "ion2": "S²⁻", "precipitate": "是", "color": "黑色"},
            {"ion1": "Pb²⁺", "ion2": "I⁻", "precipitate": "是", "color": "黃色"},
            {"ion1": "Fe³⁺", "ion2": "OH⁻", "precipitate": "是", "color": "紅褐色"},
            {"ion1": "Na⁺", "ion2": "NO₃⁻", "precipitate": "否", "color": "無"},
            {"ion1": "K⁺", "ion2": "Cl⁻", "precipitate": "否", "color": "無"}
        ]
        
        if st.button("🎲 隨機混合新離子溶液") or st.session_state.chem_q is None:
            st.session_state.chem_q = random.choice(chem_db)
            
        q = st.session_state.chem_q
        st.info(f"💧 當前溶液混合：將含有 **{q['ion1']}** 的溶液與含有 **{q['ion2']}** 的溶液混合...")
        
        user_precip = st.radio("請問是否會產生沉澱？", ["是", "否"], horizontal=True)
        user_color = st.text_input("如果會沉澱，請輸入沉澱顏色（若不會沉澱請輸入'無'）：", placeholder="例如：白色、黃色、無")
        
        if st.button("送出化學化驗結果"):
            if user_precip == q['precipitate'] and (user_color.strip() == q['color']):
                st.success(f"🎉 完全正確！{q['ion1']} 與 {q['ion2']} 確實{'會' if q['precipitate']=='是' else '不會'}沉澱，顏色為 {q['color']}！")
                st.session_state.game_score += 15
            else:
                st.error(f"❌ 化驗失敗！正確答案是：是否沉澱 ➔ 【{q['precipitate']}】，沉澱顏色 ➔ 【{q['color']}】")
                
    # ----- 遊戲 B：數學質數分解王 -----
    elif game_type == "🔢 數學質數分解王":
        st.markdown("#### 🔢 質數終結者 - 隨機大數因式分解")
        st.caption("遊戲規則：系統會由小到大、隨機生成一個高難度整數。請輸入它的『標準分解式』（例如：12 = 2^2 * 3）。")
        
        math_pool = [12, 24, 45, 84, 91, 105, 143, 221, 323, 493, 1001]
        
        if st.button("🎲 抽取下一道隨機大數") or st.session_state.math_num is None:
            st.session_state.math_num = random.choice(math_pool)
            
        n = st.session_state.math_num
        st.info(f"🔢 當前挑戰數字： **{n}**")
        
        user_factor = st.text_input("請輸入其標準分解式（格式範例： 2^2 * 3 或 11 * 13）：")
        
        def get_prime_factors_string(num):
            factors = []
            d = 2
            temp = num
            while d * d <= temp:
                if temp % d == 0:
                    count = 0
                    while temp % d == 0:
                        count += 1
                        temp //= d
                    factors.append(f"{d}^{count}" if count > 1 else f"{d}")
                d += 1
            if temp > 1:
                factors.append(f"{temp}")
            return " * ".join(factors)
            
        if st.button("驗證因式分解答案"):
            correct_ans = get_prime_factors_string(n)
            clean_user = user_factor.replace(" ", "")
            clean_correct = correct_ans.replace(" ", "")
            
            if clean_user == clean_correct or (n == 91 and clean_user == "7*13") or (n == 143 and clean_user == "11*13"):
                st.success(f"🎉 答對了！{n} 的標準分解式完美終結 ➔ {correct_ans}！")
                st.session_state.game_score += 25
            else:
                st.error(f"❌ 分解錯誤！{n} 的正確標準分解式應該是：【 {correct_ans} 】")
                
    st.divider()
    st.metric(label="🏆 遊戲競技場總積分", value=f"{st.session_state.game_score} XP")
