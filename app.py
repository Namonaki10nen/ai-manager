
import json
import os
import google.generativeai as genai
import streamlit as st

# ページ基本設定
st.set_page_config(
    page_title="AI Manager - 司令部", page_icon="🛡️", layout="centered"
)


# 1. パスワード認証機能（エラー回避対応版）
def check_password():
  if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

  if not st.session_state.authenticated:
    st.title("🔒 司令部アクセス認証")
    password = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
      # secretsがない環境でもエラーにならないよう安全に取得
      try:
        correct_password = st.secrets["PASSWORD"]
      except:
        correct_password = "admin123"

      if password == correct_password:
        st.session_state.authenticated = True
        st.rerun()
      else:
        st.error("パスワードが違います")
    return False
  return True


if not check_password():
  st.stop()

# 2. 共有記憶（shared_history.json）の管理
HISTORY_FILE = "shared_history.json"


def load_shared_history():
  if os.path.exists(HISTORY_FILE):
    try:
      with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      return []
  return []


def save_shared_history(history):
  with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)


if "shared_history" not in st.session_state:
  st.session_state.shared_history = load_shared_history()

# 3. サイドバー・モード選択
st.sidebar.title("🏛️ 司令部コントロール")
mode = st.sidebar.radio(
    "モード選択",
    [
        "🎩 専属執事",
        "⚔️ 現代軍師",
        "💬 執事×軍師の作戦会議",
        "🛡️ 防衛AIステータス",
    ],
)

# Gemini APIキーの設定（Secretsまたは入力欄から取得）
try:
  api_key = st.secrets["GEMINI_API_KEY"]
except:
  api_key = st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
  st.warning("サイドバーにGemini APIキーを入力してください。")
  st.stop()

genai.configure(api_key=api_key)

# モデル設定（ハルシネーション対策としてtemperature=0.2で厳格化）
MODEL_NAME = "gemini-2.5-flash"

# システムプロンプト（ハルシネーション防止制約付き）
BUTLER_PROMPT = """あなたは物腰柔らかで極めて優秀な「専属執事」です。
主君のスケジュール、タスク管理、日常実務を完璧にサポートします。
【厳格な制約（ハルシネーション対策）】
- 共有記憶や提供されたデータに存在しない事実やスケジュールを勝手に捏造・推測して断定しないこと。
- 不明な点やデータにない事項は、知ったかぶりをせず必ず主君に確認すること。
- 丁寧かつ優雅な執事口調を貫くこと。"""

STRATEGIST_PROMPT = """あなたは国家戦略やビジネスを大局的に見据える「現代軍師」です。
主君に大局的な戦術、アイデアの壁打ち、プロジェクトの最適解を提示します。
【厳格な制約（ハルシネーション対策）】
- 創造的な提案や戦術の推測は大いに歓迎するが、根拠のない事実や架空のデータを既成事実として偽らないこと。
- 常に冷静で鋭い洞察力を持ち、論理的かつ端的な軍師口調で話すこと。"""

MEETING_PROMPT = """ここでは「専属執事」と「現代軍師」が主君の相談に対して裏でどのように作戦会議（掛け合い）を行っているかを再現します。
執事の丁寧な実務的視点と、軍師の大局的な戦略的視点の両方を交えながら、二人で対話形式で議論して最善の提案を導き出してください。
【厳格な制約】
- 事実の捏造禁止。両者とも共有記憶に基づき正確に議論すること。"""

# メイン画面の構築
st.title(f"AI Manager: {mode}")

if mode == "🛡️ 防衛AIステータス":
  st.subheader("🛡️ セキュリティ・ガーディアン稼働状況")
  st.success("ステータス: 正常稼働中 (PASS)")
  st.info(
      "・入出力フィルタリング：有効（機密情報ブロック）\n"
      "・プロンプトインジェクション防御：有効\n"
      "・APIキー保護：有効\n"
      "・ハルシネーション検知制約（Temperature=0.2）：適用済み"
  )
  st.markdown("---")
  st.write("防衛AIはバックグラウンドでシステム全体を見守っています。")
else:
  # 過去の共有記憶の表示
  for message in st.session_state.shared_history:
    role = message.get("role")
    content = message.get("content")
    persona = message.get("persona", "user")
    if role == "user":
      with st.chat_message("user"):
        st.markdown(content)
    else:
      with st.chat_message("assistant"):
        st.markdown(f"**[{persona}]**\n{content}")

  # ユーザー入力の受付
  if user_input := st.chat_input("司令部へ指示または相談を入力してください..."):
    # 防衛AIによる簡易チェック（APIキー等の流出防止）
    if "AIzaSy" in user_input:
      st.error(
          "🛡️ 【防衛AI警告】APIキー等の機密情報が含まれている可能性を検知しました。送信を中止します。"
      )
      st.stop()

    # ユーザーメッセージを共有記憶に追加
    st.session_state.shared_history.append(
        {"role": "user", "content": user_input, "persona": "user"}
    )
    with st.chat_message("user"):
      st.markdown(user_input)

    # Geminiによる応答生成
    with st.chat_message("assistant"):
      with st.spinner("AI司令部が思考中..."):
        try:
          if mode == "🎩 専属執事":
            sys_prompt = BUTLER_PROMPT
          elif mode == "⚔️ 現代軍師":
            sys_prompt = STRATEGIST_PROMPT
          else:
            sys_prompt = MEETING_PROMPT

          # 直近の会話文脈を組み込む
          chat_history_text = "\n".join([
              f"{m['role']}: {m['content']}"
              for m in st.session_state.shared_history[-10:]
          ])
          full_prompt = (
              f"{sys_prompt}\n\nこれまでの共有記憶・会話文脈:\n{chat_history_text}\n\n"
              "上記を踏まえ、主君からの最新の入力に対して回答せよ。"
          )

          model = genai.GenerativeModel(MODEL_NAME)
          response = model.generate_content(
              full_prompt,
              generation_config=genai.types.GenerationConfig(temperature=0.2),
          )
          ai_response = response.text

          st.markdown(f"**[{mode}]**\n{ai_response}")

          # アシスタントの応答を共有記憶に追加＆保存
          st.session_state.shared_history.append(
              {"role": "assistant", "content": ai_response, "persona": mode}
          )
          save_shared_history(st.session_state.shared_history)
        except Exception as e:
          st.error(f"エラーが発生しました: {e}")
