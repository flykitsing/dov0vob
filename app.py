import streamlit as st
import os, requests, random

def go_to_menu(): st.session_state.current_page = "menu"

def call_ai(p):
    k = os.environ.get("GEMINI_API_KEY")
    if not k: return "【未設定 GEMINI_API_KEY】"
    try:
        from google import genai
        return genai.Client(api_key=k).models.generate_content(model="gemini-2.5-flash", contents=p).text
    except Exception as e: return f"失敗: {e}"

st.set_page_config(page_title="新式學習工具", layout="wide")
for k, v in {"current_page": "menu", "notes": [], "chem_q": None, "math_q": None}.items():
    if k not in st.session_state: st.session_state[k] = v

with st.sidebar:
    st.header("🧠 學習工具")
    sub = st.selectbox("科目", ["數學", "物理", "地科", "化學", "其他"])
    for n in [x for x in st.session_state.notes if x["sub"] == sub][-2:]: st.info(f"• {n['con']}")
    note_txt = st.text_area("新增筆記")
    if st.button("儲存筆記") and note_txt.strip():
        st.session_state.notes.append({"sub": sub, "con": note_txt.strip()})
        st.rerun()

if st.session_state.current_page == "menu":
    st.title("🧠 新式學習工具")
    cols = st.columns(4)
    pages = [("🚀 智慧解題", "solve"), ("📝 歷史複習", "review"), ("🎮 遊戲場", "game"), ("📒 記事本", "notebook")]
    for i, (title, p_name) in enumerate(pages):
        with cols[i]:
            if st.button(title, use_container_width=True, type="primary"): st.session_state.current_page = p_name; st.rerun()

elif st.session_state.current_page == "solve":
    st.button("⬅️ 回主畫面", on_click=go_to_menu)
    st.subheader("🚀 智慧解題系統")
    q = st.text_area("請輸入想研究的題目：")
    if st.button("啟動解題", type="primary") and q.strip():
        with st.spinner("思考中..."): st.markdown(call_ai(f"請詳細解答此考點並給出核心觀念：{q}"))

elif st.session_state.current_page == "review":
    st.button("⬅️ 回主畫面", on_click=go_to_menu)
    st.subheader("📝 動態觀念複習")
    q_input = st.text_area("輸入你想複習的觀念：")
    if st.button("讓 AI 進行觀念抽查") and q_input.strip():
        with st.spinner("評估中..."): st.write(call_ai(f"請針對「{q_input}」這個觀念出一個問答題並給詳解。"))

elif st.session_state.current_page == "game":
    st.button("⬅️ 回主畫面", on_click=go_to_menu)
    st.subheader("🎮 學術終結者競技場")
    g_type = st.selectbox("選擇遊戲", ["化學沉澱", "數學分解"])
    if g_type == "化學沉澱":
        if st.button("換一題") or st.session_state.chem_q is None: st.session_state.chem_q = random.choice([("Ag+", "Cl-", "白色"), ("Ba2+", "SO42-", "白色")])
        st.warning(f"💧 離子混合： **{st.session_state.chem_q[0]}** 與 **{st.session_state.chem_q[1]}** 是什麼顏色沉澱？")
        ans = st.text_input("輸入顏色")
        if st.button
