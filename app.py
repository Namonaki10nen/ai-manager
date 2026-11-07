import json
import streamlit as st
from groq import Groq
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

st.set_page_config(
    page_title="AI Manager",
    page_icon="🛡️",
    layout="centered"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    .stTextInput input, .stChatInput input {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    .stButton button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    [data-testid="stChatMessage"] {
        background: linear-gradient(135deg, #111827 0%, #1a2333 100%);
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    [data-testid="stChatMessage"] img {
        border-radius: 50%;
        object-fit: cover;
    }
</style>
""", unsafe_allow_html=True)

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🛡️ ACCESS CONTROL</h2>", unsafe_allow_html=True)
        password = st.text_input("パスワードを入力", type="password")
        if st.button("認証", use_container_width=True):
            if password == st.secrets.get("PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

def get_calendar_service():
    try:
        creds_json = json.loads(st.secrets["google"]["credentials"])
        creds = Credentials.from_service_account_info(
            creds_json, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        return build("calendar", "v3", credentials=creds)
    except Exception:
        return None

if check_password():
    st.markdown("<h1 style='color: #38bdf8; font-size: 1.6rem;'>⚡ AI MANAGER</h1>", unsafe_allow_html=True)

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("GROQ_API_KEYが設定されていません")
        st.stop()

    client = Groq(api_key=api_key)

    st.sidebar.markdown("<h3 style='color: #38bdf8;'>コントロール</h3>", unsafe_allow_html=True)
    mode = st.sidebar.radio("モード", ["専属執事", "現代軍師", "作戦会議", "防衛AIステータス"])

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if mode not in st.session_state.chat_history:
        st.session_state.chat_history[mode] = []
    if "shared_notes" not in st.session_state:
        st.session_state.shared_notes = []

    prompts = {
        "専属執事": "あなたは最高峰の専属執事です。丁寧で品格ある言葉遣い（〜でございます等）で主人を支えてください。",
        "現代軍師": "あなたは冷徹かつ明晰な現代の軍師です。感情を排し、論理的かつ戦略的に進言してください。",
        "作戦会議": (
            "あなたは作戦会議システムです。「専属執事」と「現代軍師」の2人の視点を同時に展開してください。"
            "必ず以下の形式で出力してください：\n"
            "---BUTLER---\n(執事の意見)\n\n"
            "---GENERAL---\n(軍師の意見)\n\n"
            "---SUMMARY---\n(総括・作戦案)"
        ),
        "防衛AIステータス": "あなたは独立した防衛管理AIです。機械的・客観的なシステムレポートのみを行ってください。"
    }

    base = prompts.get(mode, "あなたは優秀なアシスタントです。")
    cal_rule = ""
    if mode != "防衛AIステータス":
        cal_rule = (
            "\n\n予定登録の指示がある場合、回答の最後に必ず以下を出力せよ:\n"
            "```calendar_event\n"
            "{\n"
            '  "summary": "タイトル",\n'
            '  "start": "YYYY-MM-DDTHH:MM:SS",\n'
            '  "end": "YYYY-MM-DDTHH:MM:SS",\n'
            '  "description": "詳細"\n'
            "}\n"
            "```"
        )

    notes = ""
    if st.session_state.shared_notes:
        notes = "\n\n【共有ノート】\n" + "\n".join(st.session_state.shared_notes[-6:])

    system_prompt = base + cal_rule + notes

    st.markdown(f"<p style='color: #38bdf8; font-weight: bold;'>ACTIVE: {mode}</p>", unsafe_allow_html=True)
    messages = st.session_state.chat_history[mode]

    u_avatar = "https://api.dicebear.com/7.x/avataaars/svg?seed=User"
    b_avatar = "https://api.dicebear.com/7.x/bottts/svg?seed=Butler"
    g_avatar = "https://api.dicebear.com/7.x/bottts/svg?seed=General"
    s_avatar = "https://api.dicebear.com/7.x/bottts/svg?seed=Strategy"

    for m in messages:
        if m["role"] == "user":
            with st.chat_message("user", avatar=u_avatar):
                st.write(m["content"])
        else:
            with st.chat_message("assistant", avatar=b_avatar):
                st.write(m["content"])

    if prompt := st.chat_input("指示を入力..."):
        messages.append({"role": "user", "content": prompt})
        st.session_state.shared_notes.append(f"[{mode}] {prompt}")

        with st.chat_message("user", avatar=u_avatar):
            st.write(prompt)

        with st.chat_message("assistant", avatar=b_avatar):
            try:
                full_msgs = [{"role": "system", "content": system_prompt}]
                for m in messages:
                    full_msgs.append({"role": m["role"], "content": m["content"]})

                res = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=full_msgs
                )
                reply = res.choices[0].message.content

                if "```calendar_event" in reply and mode != "防衛AIステータス":
                    parts = reply.split("

 



