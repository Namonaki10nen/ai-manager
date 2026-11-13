import json
import os
import streamlit as st
from groq import Groq
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime

st.set_page_config(
    page_title="AI Manager - Command Center",
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
</style>
""", unsafe_allow_html=True)

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🛡️ COMMAND CENTER ACCESS</h2>", unsafe_allow_html=True)
        password = st.text_input("アクセスパスワードを入力", type="password")
        if st.button("システム認証", use_container_width=True):
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

MEMORY_FILE = "shared_memory.json"

def load_shared_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_shared_memory(notes):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if check_password():
    st.markdown("<h1 style='color: #38bdf8; font-size: 1.6rem;'>⚡ AI MANAGER : 司令部システム</h1>", unsafe_allow_html=True)

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("GROQ_API_KEYが設定されていません")
        st.stop()

    client = Groq(api_key=api_key)

    st.sidebar.markdown("<h3 style='color: #38bdf8;'>🔧 司令部コントロール</h3>", unsafe_allow_html=True)
    mode = st.sidebar.radio("モード選択", ["専属執事", "現代軍師", "作戦会議", "防衛AIステータス"])

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if mode not in st.session_state.chat_history:
        st.session_state.chat_history[mode] = []
        
    if "shared_notes" not in st.session_state:
        st.session_state.shared_notes = load_shared_memory()

    if "welcomed" not in st.session_state:
        st.session_state.welcomed = set()

    prompts = {
        "専属執事": "あなたは最高峰の専属執事です。丁寧で品格ある言葉遣い（〜でございます等）で主人を支えてください。",
        "現代軍師": "あなたは冷徹かつ明晰な現代の軍師です。感情を排し、論理的かつ戦略的に進言してください。",
        "作戦会議": (
            "あなたは作戦会議システムです。必ず「専属執事」と「現代軍師」の両視点から発言してください。\n"
            "【出力形式の厳守】回答は必ず以下のタグで正確に分割して出力してください：\n\n"
            "---BUTLER---\n(執事としての意見・丁寧な気配り)\n\n"
            "---GENERAL---\n(軍師としての意見・戦略的分析)\n\n"
            "---SUMMARY---\n(全体の総括・推奨作戦)"
        ),
        "防衛AIステータス": "あなたは独立した防衛管理AIです。機械的・客観的なシステムレポートのみを行ってください。"
    }

    base = prompts.get(mode, "あなたは優秀なアシスタントです。")
    
    cal_rule = ""
    if mode != "防衛AIステータス":
        now_date_str = datetime.now().strftime("%Y-%m-%d")
        cal_rule = (
            f"\n\n【絶対遵守：カレンダー連携機能】\n"
            f"現在の日付は {now_date_str} です。\n"
            "ユーザーが「予定を入れて」「〜の予定」「スケジュール追加」など、カレンダー登録を意図する発言をした場合、"
            "通常の返答テキストの末尾に、必ず以下のような正確なJSON形式のコードブロックを含めてください。\n"
            "日付（YYYY-MM-DDTHH:MM:SS）は必ず現在の基準から算出して埋めてください。\n\n"
            "```calendar_event\n"
            "{\n"
            '  "summary": "予定のタイトル",\n'
            '  "start": "2026-11-14T15:00:00",\n'
            '  "end": "2026-11-14T16:00:00",\n'
            '  "description": "詳細"\n'
            "}\n"
            "```"
        )

    notes = ""
    if st.session_state.shared_notes:
        notes = "\n\n【司令部の共有ノート・これまでの経緯（長期記憶）】\n" + "\n".join(st.session_state.shared_notes[-10:])

    system_prompt = base + cal_rule + notes

    st.markdown(f"<p style='color: #38bdf8; font-weight: bold;'>ACTIVE MODE : 【 {mode} 】</p>", unsafe_allow_html=True)
    messages = st.session_state.chat_history[mode]

    def render_assistant_reply(content, current_mode):
        if current_mode == "作戦会議" and "---BUTLER---" in content and "---GENERAL---" in content:
            try:
                parts = content.split("---GENERAL---")
                butler_text = parts[0].replace("---BUTLER---", "").strip()
                
                remaining = parts[1].split("---SUMMARY---")
                general_text = remaining[0].strip()
                summary_text = remaining[1].strip() if len(remaining) > 1 else ""

                with st.chat_message("assistant", avatar="🛡️"):
                    st.markdown("**🛡️ 専属執事**")
                    st.write(butler_text)

                with st.chat_message("assistant", avatar="⚔️"):
                    st.markdown("**⚔️ 現代軍師**")
                    st.write(general_text)

                if summary_text:
                    with st.chat_message("assistant", avatar="📊"):
                        st.markdown("**📊 総括・作戦案**")
                        st.write(summary_text)
            except Exception:
                with st.chat_message("assistant", avatar="🛡️"):
                    st.write(content)
        else:
            icon = "🛡️" if current_mode == "専属執事" else ("⚔️" if current_mode == "現代軍師" else "🤖")
            with st.chat_message("assistant", avatar=icon):
                st.write(content)

    if mode not in st.session_state.welcomed and not messages:
        st.session_state.welcomed.add(mode)
        now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        welcome_prompt = f"現在時刻は {now_str} です。主人（ユーザー）が司令部にログインしました。これまでの共有ノートの記憶を踏まえ、本日の状況やサポートの意気込みを簡潔にブリーフィング（挨拶）してください。"
        
        try:
            res = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": welcome_prompt}
                ]
            )
            welcome_reply = res.choices[0].message.content
            messages.append({"role": "assistant", "content": welcome_reply})
        except Exception:
            pass

    for m in messages:
        if m["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.write(m["content"])
        else:
            render_assistant_reply(m["content"], mode)

    if prompt := st.chat_input("司令部へ指示または相談を入力してください..."):
        messages.append({"role": "user", "content": prompt})
        st.session_state.shared_notes.append(f"[{mode}] ユーザー: {prompt}")
        save_shared_memory(st.session_state.shared_notes)

        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

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
                parts = reply.split("```calendar_event")
                reply = parts[0].strip()
                try:
                    ev = json.loads(parts[1].split("```")[0].strip())
                    srv = get_calendar_service()
                    if srv:
                        body = {
                            "summary": ev.get("summary", "予定"),
                            "description": ev.get("description", ""),
                            "start": {"dateTime": ev["start"], "timeZone": "Asia/Tokyo"},
                            "end": {"dateTime": ev["end"], "timeZone": "Asia/Tokyo"},
                            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 1440}]}
                        }
                        srv.events().insert(calendarId=st.secrets["google"].get("calendar_id", "primary"), body=body).execute()
                        reply += "\n\n✅ **[SYSTEM] カレンダー登録＆前日通知設定完了**"
                except Exception as ex:
                    reply += f"\n\n⚠️ カレンダーエラー: {ex}"

            render_assistant_reply(reply, mode)

            messages.append({"role": "assistant", "content": reply})
            st.session_state.shared_notes.append(f"[{mode}] AI: {reply[:35]}...")
            save_shared_memory(st.session_state.shared_notes)
        except Exception as e:
            st.error(f"エラー: {e}")


