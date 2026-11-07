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
    st.title("AI Manager")

    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("SecretsにGROQ_API_KEYが設定されていません")
        st.stop()

    client = Groq(api_key=api_key)

    # サイドバーのコントロール・モード選択
    st.sidebar.title("司令部コントロール")
    mode = st.sidebar.radio(
        "モード選択",
        ["専属執事", "現代軍師", "作戦会議", "防衛AIステータス"]
    )

    # 1. モードごとに完全に独立した会話履歴を管理する辞書
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}

    if mode not in st.session_state.chat_history:
        st.session_state.chat_history[mode] = []

    # 2. 全モードの裏の動きを同期する「共有ノート」
    if "shared_notes" not in st.session_state:
        st.session_state.shared_notes = []

    # 各モードのキャラクター指示（防衛AIも完全に独立・特化）
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
            "回答は必ず以下のフォーマットで出力してください：\n"
            "【執事の意見】\n(執事の立場から、主人を気遣う丁寧なトーン)\n\n"
            "【軍師の意見】\n(軍師の立場から、冷徹かつ戦略的なトーン)\n\n"
            "【総括・作戦案】\n(2人の意見を統合した最終的な推奨アクション)"
        ),
        "防衛AIステータス": (
            "あなたは司令部の独立した防衛・治安維持管理AIです。"
            "常に裏でネットワークの治安維持、セキュリティ監視、アクセス制御を行っています。"
            "口調はSF映画のシステムAIのように徹底して機械的・客観的であり、「ステータス確認」「防衛網正常」「異常なし」などのシステム・治安維持に関するレポートのみを行ってください。"
            "他のモードの人間的な相談や対話スタイルには一切流されず、孤高の防衛システムとしての役割を貫いてください。"
        )
    }

    base_prompt = system_prompts.get(mode, "あなたは優秀なアシスタントです。")

    # 裏の共有ノートをシステムプロンプトにインジェクト
    shared_context = ""
    if st.session_state.shared_notes:
        shared_context = "\n\n【司令部全体の共有ノート（他モードでのやり取り）】\n" + "\n".join([f"- {note}" for note in st.session_state.shared_notes[-8:]])

    current_system_prompt = base_prompt + shared_context

    # 現在のモード名を表示
    st.subheader(f"現在のモード: 【{mode}】")

    # 現在選択しているモード専用の会話履歴を取得
    current_messages = st.session_state.chat_history[mode]

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("司令部へ指示または相談を入力してください..."):
        current_messages.append({"role": "user", "content": prompt})
        st.session_state.shared_notes.append(f"[{mode}] ユーザー: {prompt}")

        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            try:
                full_messages = [{"role": "system", "content": current_system_prompt}]
                for m in current_messages:
                    full_messages.append({"role": m["role"], "content": m["content"]})

                completion = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=full_messages
                )
                reply = completion.choices[0].message.content
                st.write(reply)
                
                current_messages.append({"role": "assistant", "content": reply})
                st.session_state.shared_notes.append(f"[{mode}] 回答: {reply[:40]}...")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

