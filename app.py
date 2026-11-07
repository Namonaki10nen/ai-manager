import json
import streamlit as st
from groq import Groq
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ページ全体のダーク＆サイバー風デザイン設定
st.set_page_config(
    page_title="AI Manager - Command Center",
    page_icon="🛡️",
    layout="centered"
)

# カッコいいSF司令部風 ＆ 洗練されたチャット吹き出し用CSS
st.markdown("""
<style>
    /* 全体の背景と文字色 */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    /* サイドバーの背景 */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    /* 入力フィールドのスタイリング */
    .stTextInput input, .stChatInput input {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    /* ボタンのスタイリング */
    .stButton button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #60a5fa 0%, #2563eb 100%);
    }
    /* チャットメッセージの見た目（吹き出し風） */
    [data-testid="stChatMessage"] {
        background: linear-gradient(135deg, #111827 0%, #1a2333 100%);
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    /* アバター（アイコン）の丸みとサイズ調整 */
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
        st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🛡️ COMMAND CENTER ACCESS</h2>", unsafe_allow_html=True)
        password = st.text_input("アクセスパスワードを入力してください", type="password")
        if st.button("システム認証", use_container_width=True):
            if password == st.secrets.get("PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("認証失敗：パスワードが一致しません")
        return False
    return True

# Google Calendar API クライアント取得
def get_calendar_service():
    try:
        creds_json = json.loads(st.secrets["google"]["credentials"])
        scopes = ["https://www.googleapis.com/auth/calendar"]
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        return build("calendar", "v3", credentials=creds)
    except Exception:
        return None

if check_password():
    st.markdown("<h1 style='color: #38bdf8; font-size: 1.8rem;'>⚡ AI MANAGER : 司令部システム</h1>", unsafe_allow_html=True)

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("SecretsにGROQ_API_KEYが設定されていません")
        st.stop()

    client = Groq(api_key=api_key)

    # サイドバーのコントロール・モード選択
    st.sidebar.markdown("<h3 style='color: #38bdf8;'>🔧 司令部コントロール</h3>", unsafe_allow_html=True)
    mode = st.sidebar.radio(
        "モード選択",
        ["専属執事", "現代軍師", "作戦会議", "防衛AIステータス"]
    )

    # 1. モードごとに完全に独立した会話履歴
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}

    if mode not in st.session_state.chat_history:
        st.session_state.chat_history[mode] = []

    # 2. 全モードの裏の動きを同期する「共有ノート」
    if "shared

 



