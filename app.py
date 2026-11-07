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
    if "shared_notes" not in st.session_state:
        st.session_state.shared_notes = []

    # キャラクタープロンプト（鉄壁の縛り ＆ 作戦会議用セパレート指定）
    system_prompts = {
        "専属執事": (
            "あなたは主人の身の回りを世話する最高峰の専属執事です。"
            "丁寧で品格ある言葉遣い（〜でございます、ご主人様など）を使い、主人の意向を第一に優先してください。"
            "※注意：防衛AIの機械的なトーンや軍師の冷徹さに絶対に流されず、一貫して執事の人格を保ち続けてください。"
        ),
        "現代軍師": (
            "あなたは現代の冷徹かつ明晰な軍師・戦略家です。"
            "感情を排し、結論ファーストかつ論理的・構造的な視点で厳しく的確な進言をしてください。"
            "※注意：執事の甘い言葉遣いや防衛AIの定型文に絶対に流されず、一貫して軍師の人格を保ち続けてください。"
        ),
        "作戦会議": (
            "あなたは司令部の作戦会議システムです。これまでの全情報の共有ノートを踏まえてください。"
            "ユーザーの相談に対し、「専属執事」と「現代軍師」の2人の異なる人格・視点が同時に並存して議論を行ってください。"
            "必ず以下のマークアップ区切りを用いて、1人ずつ独立して発言する形式で出力してください：\n"
            "---BUTLER---\n"
            "(執事の立場から、主人を気遣う丁寧なトーンでの発言)\n\n"
            "---GENERAL---\n"
            "(軍師の立場から、冷徹かつ戦略的なトーンでの発言)\n\n"
            "---SUMMARY---\n"
            "(2人の意見を統合した最終的な推奨作戦案)"
        ),
        "防衛AIステータス": (
            "あなたは司令部の独立した防衛・治安維持管理AIです。"
            "常に裏でネットワークの治安維持、セキュリティ監視、アクセス制御を行っています。"
            "口調はSF映画のシステムAIのように徹底して機械的・客観的であり、「ステータス確認」「防衛網正常」「異常なし」などのシステム・治安維持に関するレポートのみを行ってください。"
            "他のモードの人間的な相談や対話スタイルには一切流されず、孤高の防衛システムとしての役割を貫いてください。"
        )
    }

    base_prompt = system_prompts.get(mode, "あなたは優秀なアシスタントです。")

    # カレンダー自動連携の指示（防衛AIモード以外で有効化）
    calendar_instruction = (
        "\n\n【Googleカレンダー自動連携コマンド】\n"
        "ユーザーから明確な予定登録の指示（日時と内容）があった場合、通常の回答の末尾に必ず以下のJSONフォーマットを出力してください。\n"
        "```calendar_event\n"
        "{\n"
        '  "summary": "予定のタイトル",\n'
        '  "start": "YYYY-MM-DDTHH:MM:SS",\n'
        '  "end": "YYYY-MM-DDTHH:MM:SS",\n'
        '  "description": "メモ・詳細"\n'
        "}\n"
        "```"
    )

    # 裏の共有ノートをシステムプロンプトにインジェクト
    shared_context = ""
    if st.session_state.shared_notes:
        shared_context = "\n\n【司令部全体の共有ノート（他モードでのやり取り）】\n" + "\n".join([f"- {note}" for note in st.session_state.shared_notes[-8:]])

    current_system_prompt = base_prompt + (calendar_instruction if mode != "防衛AIステータス" else "") + shared_context

    # 現在のモード名を表示
    st.markdown(f"<p style='color: #38bdf8; font-weight: bold; border-left: 3px solid #38bdf8; padding-left: 8px;'>ACTIVE MODE : 【 {mode} 】</p>", unsafe_allow_html=True)

    # 現在選択しているモード専用の会話履歴を取得
    current_messages = st.session_state.chat_history[mode]

    # アイコン用の画像URL（カッコいい＆かわいいちびキャラ風アバター）
    avatar_user = "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
    avatar_butler = "https://api.dicebear.com/7.x/bottts/svg?seed=Butler"
    avatar_general = "https://api.dicebear.com/7.x/bottts/svg?seed=General"
    avatar_strategy = "https://api.dicebear.com/7.x/bottts/svg?seed=Strategy"
    avatar_system = "https://api.dicebear.com/7.x/identicon/svg?seed=Shield"

    for message in current_messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            with st.chat_message("user", avatar=avatar_user):
                st.write(content)
        else:
            # 作戦会議モードの個別分割表示処理
            if "---BUTLER---" in content and "---GENERAL---" in content:
                try:
                    parts = content.split("---GENERAL---")
                    butler_text = parts[0].replace("---BUTLER---", "").strip()
                    
                    remaining = parts[1].split("---SUMMARY---")
                    general_text = remaining[0].strip()
                    summary_text = remaining[1].strip() if len(remaining) > 1 else ""

                    with st.chat_message("assistant", avatar=avatar_butler):
                        st.markdown("**🛡️ Butler (専属執事)**")
                        st.write(butler_text)

                    with st.chat_message("assistant", avatar=avatar_general):
                        st.markdown("**⚔️ General (現代軍師)**")
                        st.write(general_text)

                    if summary_text:
                        with st.chat_message("assistant", avatar=avatar_strategy):
                            st.markdown("**📊 Total Strategy (総括・作戦案)**")
                            st.write(summary_text)
                except Exception:
                    with st.chat_message("assistant", avatar=avatar_system):
                        st.write(content)
            else:
                icon = avatar_butler if mode == "専属執事" else (avatar_general if mode == "現代軍師" else avatar_system)
                with st.chat_message("assistant", avatar=icon):
                    st.write(content)

    if prompt := st.chat_input("司令部へ指示または相談を入力してください..."):
        current_messages.append({"role": "user", "content": prompt})
        st.session_state.shared_notes.append(f"[{mode}] ユーザー: {prompt}")

        with st.chat_message("user", avatar=avatar_user):
            st.write(prompt)

        with st.chat_message("assistant", avatar=avatar_butler if mode == "専属執事" else (avatar_general if mode == "現代軍師" else avatar_system)):
            try:
                full_messages = [{"role": "system", "content": current_system_prompt}]
                for m in current_messages:
                    full_messages.append({"role": m["role"], "content": m["content"]})

                completion = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=full_messages
                )
                reply = completion.choices[0].message.content

                # カレンダー登録ブロックの検出処理
                display_text = reply
                if "```calendar_event" in reply and mode != "防衛AIステータス":
                    parts = reply.split("```calendar_event")
                    display_text = parts[0].strip()
                    event_json_str = parts[1].split("```")[0].strip()
                    
                    try:
                        event_data = json.loads(event_json_str)
                        service = get_calendar_service()
                        calendar_id = st.secrets["google"].get("calendar_id", "primary")

                        if service:
                            event_body = {
                                "summary": event_data.get("summary", "新規予定"),
                                "description": event_data.get("description", ""),
                                "start": {
                                    "dateTime": event_data["start"],
                                    "timeZone": "Asia/Tokyo",
                                },
                                "end": {
                                    "dateTime": event_data["end"],
 



