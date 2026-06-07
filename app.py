import streamlit as st

# ==========================================
# 0. 核心全域工具函式 (延遲載入套件，防止白屏)
# ==========================================
def go_to_menu():
    st.session_state.current_page = "menu"

def safe_plot(code):
    try:
        import os
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

def call_gemini_backup(prompt_text):
    try:
        import os
        from google import genai
        k = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=k)
        res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_text)
        return res.text
    except:
        return "【模型運作失敗】"

def call_deepseek(prompt):
    try:
        import os
        import requests
        k = os.environ.get("DEEPSEEK_API_KEY")
        if not k:
            return call_gemini_backup(prompt)
        u = "https://api.deepseek.com/v1/chat/completions"
        hd = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        return requests.post(url=u, json=payload, headers=hd, timeout=10).json()['choices'][0]['message']['content']
    except:
        return call_gemini_backup(prompt)

def call_groq(prompt):
    try:
        import os
        import requests
        k = os.environ.get("GROQ_API_KEY")
        if not k:
            return call_gemini_backup(prompt)
        u = "https://api.groq.com/openai/v1/chat/completions"
        hd = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        return requests.post(url=u, json=payload, headers=hd, timeout=10).json()['choices'][0]['message']['content']
    except:
        return call_gemini_backup(prompt)

def run_ai_pipeline(q):
    p1 = f"請解答問題。必須附帶 Python 繪圖程式碼並包在 ```python ... ``` 區塊中，使用 plt.savefig('output_plot.png') 存檔。\n\n題目：{q}"
    draft = call_gemini_backup(p1)
    review = call_deepseek(f"請指出此解答的錯誤：\n\n{draft}")
    final = call_groq(f"請整合修正，輸出終審完美版筆記，必須包含繪圖程式碼區塊。\n\n初稿：{draft}\n建議：{review}")
    return final

def clean_and_display(txt):
    if "```python" in txt:
        parts = txt.split("```python")
        before_code = parts[0]
        after_code = parts[1].split("```")
        code_body = after_code[0]
        remaining_text = after_code[1] if len(after_code) > 1 else ""
        st.markdown(before_code + remaining_text)
        st.markdown("### 📊 觀念視覺化圖形")
        safe_plot(code_body.strip())
    else:
        st.markdown(txt)

# ==========================================
# 1. 網頁初始化與狀態管理
# ==========================================
st.set_page_config(page_title="新式學習工具", layout="wide")

if "current_page" not in st.session_state or st.session_state.current_page is None:
    st.session_state.current_page = "menu"

if "local_notes" not in st.session_state:
    st.session_state.local_notes = [
        {"subject": "數學", "content": "勘根定理的前提：函數 f(x) 必須在閉區間 [a, b] 內連續。", "time": "2026-06-01"},
        {"subject": "物理", "content": "折射定律：由司乃耳定律 n1 * sin(theta1) = n2 * sin(theta2) 得知。", "time": "2026-06-02"},
        {"subject": "地球科學", "content": "大氣河流是大氣中極端水氣輸送的狹窄通道。", "time": "2026-06-03"}
    ]

if "history_questions" not in st.session_state:
    st.session_state.history_questions = {
        "數學": ["勘根定理的幾何意義與連續性函數關係？"], "物理":
