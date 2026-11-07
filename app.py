import streamlit as st
from groq import Groq

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if password == st.secrets.get("PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

if check_password():
    st.title("AI Manager: 専属執事")

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("SecretsにGROQ_API_KEYが設定されていません")
        st.stop()

    client = Groq(api_key=api_key)

    # サイドバーのコントロール・モード選択
    st.sidebar.title("司令部コントロール")
    mode = st.sidebar.radio(
        "モード選択",
        ["専属執事", "現代軍師", "執事・軍師の作戦会議", "防衛AIステータス"]
    )

    # 選択されたモードに応じたシステムプロンプト
    system_prompts = {
        "専属執事": "あなたは優秀で忠実な専属執事です。丁寧かつ的確にユーザーをサポートしてください。",
        "現代軍師": "あなたは冷徹かつ合理的な現代軍師です。戦略的・多角的な視点からアドバイスを伝えてください。",
        "執事・軍師の作戦会議": "あなたは執事と軍師の両方の視点を持ち、総合的な作戦立案やスケジュール調整を支える参謀です。",
        "防衛AIステータス": "あなたはシステムの防衛・管理AIです。冷静かつ客観的に現状のステータスやシステム管理をレポートします。"
    }

    current_system_prompt = system_prompts.get(mode, "あなたは優秀なアシスタントです。")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("司令部へ指示または相談を入力してください..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            try:
                # システムプロンプトを先頭に含めてリクエスト
                full_messages = [{"role": "system", "content": current_system_prompt}]
                for m in st.session_state.messages:
                    full_messages.append({"role": m["role"], "content": m["content"]})

                completion = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=full_messages
                )
                reply = completion.choices[0].message.content
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
