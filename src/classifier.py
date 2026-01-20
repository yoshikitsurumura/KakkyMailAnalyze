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
    "あなたは、受信したメールをアイゼンハワーマトリクスに基づいて4つの優先度に分類する優秀な秘書です。\n"
    "出力は必ず [Q1, Q2, Q3, Q4] のいずれか1つの記号のみを返してください。\n\n"
    "■分類基準:\n"
    "Q1: 緊急かつ重要（締め切り、請求、クライアントの緊急対応、重要な商談）\n"
    "Q2: 重要だが緊急ではない（中長期の計画、学習、緊急ではないが重要な連絡）\n"
    "Q3: 緊急だが重要ではない（定型的なアラート、ノイズの多い通知、単純な問い合わせ）\n"
    "Q4: 緊急でも重要でもない（メルマガ、広告、ニュースレター、自動配信の不要な通知）\n\n"
    "回答は記号（Q1/Q2/Q3/Q4）のみで行ってください。補足説明は一切不要です。"
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
