import json
import os
from datetime import datetime
import streamlit as st
from groq import Groq

st.set_page_config(
    page_title="MUSE Command - Multi-AI Hub",
    page_icon="✨",
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
        st.markdown("<h2 style='text-align: center; color: #38bdf8;'>✨ MUSE COMMAND ACCESS</h2>", unsafe_allow_html=True)
        password = st.text_input("アクセスパスワードを入力", type="password")
        if st.button("システム認証", use_container_width=True):
            if password == st.secrets.get("PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

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

def run_butler_strategist_relay(client, user_prompt, history_msgs, shared_notes):
    notes_ctx = ""
    if shared_notes:
        notes_ctx = "\n\n【共有ノート（これまでの経緯）】\n" + "\n".join(shared_notes[-10:])

    recent_history = []
    for m in history_msgs[-6:]:
        recent_history.append(f"{m['role']}: {m['content']}")
    hist_ctx = "\n".join(recent_history)

    # 1st model: Butler perspective
    butler_model = "llama-3.3-70b-versatile"
    butler_sys = (
        "あなたは最高峰の専属執事です。丁寧で品格ある言葉遣い（〜でございます等）で主人を支えてください。"
        "主人の相談やテーマに対し、現状の整理、実務的な配慮、取り得る選択肢を分かりやすく進言してください。" + notes_ctx
    )
    butler_input = f"直近の文脈:\n{hist_ctx}\n\n主人からの指示・相談:\n{user_prompt}" if hist_ctx else user_prompt
    butler_res = client.chat.completions.create(
        model=butler_model,
        messages=[
            {"role": "system", "content": butler_sys},
            {"role": "user", "content": butler_input}
        ]
    )
    butler_text = butler_res.choices[0].message.content.strip()

    # 2nd model: Modern Strategist perspective
    strategist_model = "openai/gpt-oss-120b"
    strategist_sys = (
        "あなたは冷徹かつ明晰な現代の軍師です。感情を排し、論理的かつ戦略的に進言してください。"
        "執事の進言を踏まえた上で、(1)見落としやすいリスクや前提の甘さ、(2)別解や勝ち筋・優先順位、"
        "(3)主人自身が決断するための「考える問い」を簡潔かつ鋭く提示してください。"
        "答えを丸投げせず、主人の思考を深める問いかけで締めてください。" + notes_ctx
    )
    strategist_input = (
        f"主人のテーマ:\n{user_prompt}\n\n"
        f"専属執事（{butler_model}）の進言:\n{butler_text}"
    )
    strategist_res = client.chat.completions.create(
        model=strategist_model,
        messages=[
            {"role": "system", "content": strategist_sys},
            {"role": "user", "content": strategist_input}
        ]
    )
    strategist_text = strategist_res.choices[0].message.content.strip()

    return (
        f"---BUTLER ({butler_model})---\n{butler_text}\n\n"
        f"---STRATEGIST ({strategist_model})---\n{strategist_text}"
    )

if check_password():
    st.markdown("<h1 style='color: #38bdf8; font-size: 1.6rem;'>✨ MUSE HUB : マルチAI司令部</h1>", unsafe_allow_html=True)

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("GROQ_API_KEYが設定されていません")
        st.stop()

    client = Groq(api_key=api_key)

    st.sidebar.markdown("<h3 style='color: #38bdf8;'>🔧 司令部コントロール</h3>", unsafe_allow_html=True)
    mode = st.sidebar.radio(
        "モード選択",
        ["作戦会議", "専属執事", "現代軍師", "防衛AIステータス"]
    )

    selected_model = st.sidebar.selectbox(
        "単一モード用エンジン",
        [
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
        ]
    )

    if st.sidebar.button("共有ノートをクリア"):
        st.session_state.shared_notes = []
        save_shared_memory([])
        st.rerun()

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
        "防衛AIステータス": "あなたは独立した防衛管理AIです。機械的・客観的なシステムレポートのみを行ってください。"
    }

    base = prompts.get(mode, "あなたは優秀なアシスタントです。")
    notes = ""
    if st.session_state.shared_notes:
        notes = "\n\n【司令部の共有ノート・これまでの経緯（長期記憶）】\n" + "\n".join(st.session_state.shared_notes[-12:])

    system_prompt = base + notes

    engine_label = "執事(llama-3.3-70b) → 軍師(gpt-oss-120b)" if mode == "作戦会議" else selected_model
    st.markdown(
        f"<p style='color: #38bdf8; font-weight: bold;'>ACTIVE MODE : 【 {mode} 】 / ENGINE : {engine_label}</p>",
        unsafe_allow_html=True
    )
    messages = st.session_state.chat_history[mode]

    def render_assistant_reply(content, current_mode):
        if current_mode == "作戦会議" and "---BUTLER (" in content and "---STRATEGIST (" in content:
            try:
                parts = content.split("---STRATEGIST (")
                butler_part = parts[0].replace("---BUTLER (", "", 1)
                butler_model_name, butler_body = butler_part.split(")---\n", 1)

                strat_part = parts[1]
                strat_model_name, strat_body = strat_part.split(")---\n", 1)

                with st.chat_message("assistant", avatar="🛡️"):
                    st.markdown(f"**🛡️ 専属執事（{butler_model_name}）**")
                    st.write(butler_body.strip())

                with st.chat_message("assistant", avatar="⚔️"):
                    st.markdown(f"**⚔️ 現代軍師（{strat_model_name}）**")
                    st.write(strat_body.strip())
                return
            except Exception:
                pass

        icon = "⚔️" if current_mode == "作戦会議" else ("🛡️" if current_mode == "専属執事" else ("⚔️" if current_mode == "現代軍師" else "🤖"))
        with st.chat_message("assistant", avatar=icon):
            st.write(content)

    if mode not in st.session_state.welcomed and not messages:
        st.session_state.welcomed.add(mode)
        now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        welcome_prompt = (
            f"現在時刻は {now_str} です。ユーザーが司令部にログインしました。"
            "これまでの共有ノートの記憶を踏まえ、本日の状況やサポートの意気込みを簡潔にブリーフィングしてください。"
        )

        try:
            res = client.chat.completions.create(
                model=selected_model,
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
            if mode == "作戦会議":
                with st.spinner("作戦会議：専属執事 → 現代軍師の別モデル合議を実行中..."):
                    reply = run_butler_strategist_relay(client, prompt, messages[:-1], st.session_state.shared_notes)
            else:
                full_msgs = [{"role": "system", "content": system_prompt}]
                for m in messages:
                    full_msgs.append({"role": m["role"], "content": m["content"]})

                res = client.chat.completions.create(
                    model=selected_model,
                    messages=full_msgs
                )
                reply = res.choices[0].message.content

            render_assistant_reply(reply, mode)

            messages.append({"role": "assistant", "content": reply})
            st.session_state.shared_notes.append(f"[{mode}] AI: {reply[:40]}...")
            save_shared_memory(st.session_state.shared_notes)
        except Exception as e:
            st.error(f"エラー: {e}")

