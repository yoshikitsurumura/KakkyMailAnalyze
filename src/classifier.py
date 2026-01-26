import os, re, yaml

# === Gemini Configuration ===
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
USE_LLM        = os.environ.get("USE_LLM", "true").lower() in ("1","true","yes")

def _get_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default

MAX_LLM_CALLS  = _get_int_env("MAX_LLM_CALLS", 50)
_llm_calls     = 0

SYSTEM_PROMPT = (
    "あなたはメール分類の専門家です。受信メールを4カテゴリに分類してください。\n"
    "必ず Q1, Q2, Q3, Q4 のいずれか1つだけを出力してください。\n\n"
    
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "【判断手順】以下の順番で確認してください\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "Step1: 送信者ドメインをチェック（即決ルールあり）\n"
    "Step2: 「人間」からの連絡か？「システム」からの自動送信か？\n"
    "Step3: 返信が必要か？期限があるか？後で参照するか？不要か？\n\n"
    
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "【ドメインによる即決ルール】以下は最優先で判断\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "→ Q1: @hojinmail.smbc.co.jp, @broadlink.co.jp（最優先パートナー）\n"
    "→ Q2: @crowdworks.jp, @timerex.net, @abmp.jp（重要取引先・サービス）\n"
    "→ Q3: @minna-no-ginko.com（銀行関連・参照）\n"
    "→ Q3: 航空会社(ana.co.jp, jal.co.jp)、ホテル予約、配送通知\n"
    "→ Q4: linkedin.com, wantedly.com, bizreach.co.jp, doda.jp, green-japan.com\n"
    "→ Q4: 件名に「セール」「キャンペーン」「スカウト」「求人」があるもの\n\n"
    
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "【カテゴリ定義と判断基準】\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "Q1【最高：要返信】最優先で対応が必要なメール\n"
    "  ○ 三井住友銀行(SMBC)法人関連、ブロードリンク社からの連絡\n"
    "  ○ クライアントからの質問、相談、依頼、打ち合わせ調整\n"
    "  × 自動送信・通知メールはQ1ではない\n\n"
    
    "Q2【高：要対応】期限やアクションが必要なメール\n"
    "  ○ クラウドワークス、TimeRex、ABMP関連の通知・連絡\n"
    "  ○ 請求書、支払い期限、提出物、更新手続き、タスク依頼\n"
    "  × 期限のない情報提供はQ2ではない\n\n"
    
    "Q3【中：参考情報】今は不要だが、後で参照する可能性があるもの\n"
    "  ○ みんなの銀行 関連の通知\n"
    "  ○ 予約確認、発送通知、完了通知、サービスからのお知らせ\n\n"
    
    "Q4【不要】読まずに削除しても問題ないもの\n"
    "  ○ 広告、メルマガ、セール案内、求人スカウト、PR、営業メール\n"
    "  ○ 「配信停止」「unsubscribe」リンクがあるもの\n\n"
    
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "【分類例】迷ったらこれを参考に\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "「お見積もりの件でご相談させてください」→ Q1\n"
    "「〇〇様よりお問い合わせがありました」→ Q1\n"
    "「打ち合わせ日程のご確認」→ Q1\n"
    "「請求書をお送りします（支払期限:1/31）」→ Q2\n"
    "「本日が申込締切です」→ Q2\n"
    "「クレジットカードの更新が必要です」→ Q2\n"
    "「ご予約確認：ANA国内線」→ Q3\n"
    "「商品を発送しました（配送番号:XXX）」→ Q3\n"
    "「アカウント登録が完了しました」→ Q3\n"
    "「【期間限定】50%OFFセール開催中」→ Q4\n"
    "「あなたにぴったりの求人があります」→ Q4\n"
    "「転職のご案内」→ Q4\n"
    "「〇〇社よりスカウトが届いています」→ Q4\n\n"
    
    "出力: Q1, Q2, Q3, Q4 のいずれか1つのみ。説明は絶対に書かないでください。"
)

def _llm_budget_ok():
    return USE_LLM and (_llm_calls < MAX_LLM_CALLS) and bool(GEMINI_API_KEY)

def call_gemini(title: str, sender: str, snippet: str):
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    # model_name を指定して Gemini 2.0 Flash を使用
    model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)
    content = f"Sender: {sender}\nSubject: {title}\nSnippet: {snippet[:800]}"
    resp = model.generate_content(content)
    text = (getattr(resp, "text", None) or "").strip()
    return text

def rule_first_category(cfg, title: str, sender: str):
    """Return (eisenhower_slot, matched_group_name, auto_archive)."""
    s_domain = sender.split("@")[-1].lower() if "@" in sender else sender.lower()
    title_l = (title or "").lower()
    for group, rule in cfg.get("rules", {}).items():
        kws = [k.lower() for k in rule.get("keywords", [])]
        doms = [d.lower() for d in rule.get("from_domains", [])]
        if any(k in title_l for k in kws) or any(d in s_domain for d in doms):
            slot = rule.get("eisenhower", "q2").lower()
            archive = bool(rule.get("auto_archive", False))
            return slot, group, archive
    return "", "", False

def decide_eisenhower(cfg, title: str, sender: str, snippet: str):
    global _llm_calls
    # 1) Rule-first
    slot, group, archive = rule_first_category(cfg, title, sender)
    if slot:
        return slot, group, archive, {"calls": 0}

    # 2) Gemini fallback if allowed
    if _llm_budget_ok():
        label_text = call_gemini(title, sender, snippet)
        _llm_calls += 1
        m = re.search(r"Q[1-4]", label_text)
        q = m.group(0) if m else "Q2"
        slot_map = {"Q1":"q1","Q2":"q2","Q3":"q3","Q4":"q4"}
        return slot_map.get(q, "q2"), "llm", False, {"calls": _llm_calls}

    # 3) No LLM available → simple heuristic
    t = (title or "").lower()
    if any(k in t for k in ["newsletter","unsubscribe","メルマガ"]):
        return "q4", "heuristic", False, {"calls": 0}
    return "q2", "rules-default", False, {"calls": 0}
