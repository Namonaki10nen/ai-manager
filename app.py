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
            json.dump(notes[-50:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def clip_text(text: str, max_chars: int = 800) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...(省略)"

@st.cache_data(ttl=3600)
def fetch_available_models(api_key: str):
    fallback = ["openai/gpt-oss-120b"]
    try:
        tmp_client = Groq(api_key=api_key)
        models_resp = tmp_client.models.list()
        ids = [m.id for m in models_resp.data if getattr(m, "id", None)]
        return ids if ids else fallback
    except Exception:
        return fallback

def is_jp_friendly_model(model_id: str) -> bool:
    low = model_id.lower()
    # Avoid models known to garble Japanese output
    if "allam" in low or "whisper" in low or "guard" in low or "embedding" in low:
        return False
    return True

def pick_relay_models(available_models, preferred_second_model):
    safe_models = [m for m in available_models if is_jp_friendly_model(m)]
    if not safe_models:
        safe_models = available_models

    second_model = preferred_second_model if preferred_second_model in safe_models else (
        "openai/gpt-oss-120b" if "openai/gpt-oss-120b" in safe_models else safe_models[0]
    )

    preferred_order_keywords = ["gpt-oss", "qwen", "llama-3.3", "llama-3.1", "gemma", "deepseek", "llama"]
    candidates = [m for m in safe_models if m != second_model]
    if candidates:
        candidates.sort(
            key=lambda m: next(
                (i for i, kw in enumerate(preferred_order_keywords) if kw in m.lower()),
                len(preferred_order_keywords)
            )
        )
        first_model = candidates[0]
    else:
        first_model = second_model

    return first_model, second_model

def run_butler_strategist_relay(client, user_prompt, history_msgs, shared_notes, available_models, preferred_second_model):
    notes_ctx = ""
    if shared_notes:
        clipped_notes = [clip_text(n, 160) for n in shared_notes[-6:]]
        notes_ctx = "\n\n【共有ノート（抜粋）】\n" + "\n".join(clipped_notes)

    recent_history = []
    for m in history_msgs[-4:]:
        recent_history.append(f"{m['role']}: {clip_text(m['content'], 350)}")
    hist_ctx = "\n".join(recent_history)

    butler_model, strategist_model = pick_relay_models(available_models, preferred_second_model)

    butler_sys = (
        "あなたは最高峰の専属執事です。自然な日本語で、丁寧かつ品格ある言葉遣い（〜でございます等）で主人を支えてください。"
        "主人の相談やテーマに対し、現状の整理、実務的な配慮、取り得る選択肢を簡潔かつ分かりやすく進言してください。" + notes_ctx
    )
    butler_input = f"直近の文脈:\n{hist_ctx}\n\n主人からの指示・相談:\n{clip_text(user_prompt, 800)}" if hist_ctx else clip_text(user_prompt, 800)
    butler_res = client.chat.completions.create(
        model=butler_model,
        max_tokens=900,
        messages=[
            {"role": "system", "content": butler_sys},
            {"role": "user", "content": butler_input}
        ]
    )
    butler_text = clip_text(butler_res.choices[0].message.content or "", 1200)

    strategist_sys = (
        "あなたは冷徹かつ明晰な現代の軍師です。自然な日本語で、感情を排し、論理的かつ戦略的に進言してください。"
        "執事の進言を踏まえた上で、(1)見落としやすいリスクや前提の甘さ、(2)別解や勝ち筋・優先順位、"
        "(3)主人自身が決断するための「考える問い」を簡潔かつ鋭く提示してください。"
        "答えを丸投げせず、主人の思考を深める問いかけで締めてください。" + notes_ctx
    )
    strategist_input = (
        f"主人のテーマ:\n{clip_text(user_prompt, 600)}\n\n"
        f"専属執事（{butler_model}）の進言:\n{butler_text}"
    )
    strategist_res = client.chat.completions.create(
        model=strategist_model,
        max_tokens=1100,
        messages=[
            {"role": "system", "content": strategist_sys},
            {"role": "user", "content": strategist_input}
        ]
    )
    strategist_text = (strategist_res.choices[0].message.content or "").strip()

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
    available_models = fetch_available_models(api_key)

    st.sidebar.markdown("<h3 style='color: #38bdf8;'>🔧 司令部コントロール</h3>", unsafe_allow_html=True)
    mode = st.sidebar.radio(
        "モード選択",
        ["作戦会議", "専属執事", "現代軍師", "防衛AIステータス"]
    )

    default_idx = available_models.index("openai/gpt-oss-120b") if "openai/gpt-oss-120b" in available_models else 0
    selected_model = st.sidebar.selectbox(
        "使用エンジン（利用可能モデルから自動取得）",
        available_models,
        index=default_idx
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
        "専属執事": "あなたは最高峰の専属執事です。自然な日本語で、丁寧かつ品格ある言葉遣い（〜でございます等）で主人を支えてください。",
        "現代軍師": "あなたは冷徹かつ明晰な現代の軍師です。自然な日本語で、感情を排し、論理的かつ戦略的に進言してください。",
        "防衛AIステータス": "あなたは独立した防衛管理AIです。機械的・客観的なシステムレポートのみを行ってください。"
    }

    base = prompts.get(mode, "あなたは優秀なアシスタントです。")
    notes = ""
    if st.session_state.shared_notes:
        clipped_notes = [clip_text(n, 160) for n in st.session_state.shared_notes[-6:]]
        notes = "\n\n【司令部の共有ノート（抜粋）】\n" + "\n".join(clipped_notes)

    system_prompt = base + notes

    if mode == "作戦会議":
        m1, m2 = pick_relay_models(available_models, selected_model)
        engine_label = f"執事({m1}) → 軍師({m2})"
    else:
        engine_label = selected_model

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
                max_tokens=600,
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
        st.session_state.shared_notes.append(f"[{mode}] ユーザー: {clip_text(prompt, 120)}")
        save_shared_memory(st.session_state.shared_notes)

        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

        try:
            if mode == "作戦会議":
                with st.spinner("作戦会議：専属執事 → 現代軍師の別モデル合議を実行中..."):
                    reply = run_butler_strategist_relay(
                        client, prompt, messages[:-1], st.session_state.shared_notes,
                        available_models, selected_model
                    )
            else:
                full_msgs = [{"role": "system", "content": system_prompt}]
                for m in messages[-8:]:
                    full_msgs.append({"role": m["role"], "content": clip_text(m["content"], 600)})

                res = client.chat.completions.create(
                    model=selected_model,
                    max_tokens=1100,
                    messages=full_msgs
                )
                reply = res.choices[0].message.content

            render_assistant_reply(reply, mode)

            messages.append({"role": "assistant", "content": reply})
            st.session_state.shared_notes.append(f"[{mode}] AI: {clip_text(reply, 120)}")
            save_shared_memory(st.session_state.shared_notes)
        except Exception as e:
            st.error(f"エラー: {e}")
