import os, yaml, time
from typing import Dict
from src.gmail_client import gmail_service, list_messages, get_message, ensure_labels, modify_labels, archive_message
from src.classifier import decide_eisenhower

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1","true","yes")
LOG_MASKING = os.environ.get("LOG_MASKING", "true").lower() in ("1","true","yes")
CFG_PATH = os.path.join("config", "categories.yaml")

def load_cfg() -> Dict:
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def header_value(headers, name: str) -> str:
    for h in headers:
        if h.get("name","").lower() == name.lower():
            return h.get("value","")
    return ""

def mask_sender(s):
    if not s:
        return ""
    # "Name <user@example.com>" → "user@…"
    at = s.split("@")[0] if "@" in s else s
    return f"{at}@…"

def head(text, n=10):
    text = text or ""
    return (text[:n] + "…") if len(text) > n else text

def safe(s):  # cheap printable
    return (s or "").replace("\n"," ").replace("\r"," ")

def run():
    cfg = load_cfg()
    svc = gmail_service()
    q = cfg.get("defaults", {}).get("gmail_query", 'label:inbox newer_than:7d')
    msgs = list_messages(svc, q, max_results=50)
    if not msgs:
        print("No messages to process.")
        return

    labels_needed = list(cfg["eisenhower_labels"].values()) + [cfg["eisenhower_labels"]["processed"]]
    name_to_id = ensure_labels(svc, labels_needed)
    processed_label_id = name_to_id[cfg["eisenhower_labels"]["processed"]]

    for m in msgs:
        msg = get_message(svc, m["id"])
        label_ids = set(msg.get("labelIds", []))
        if processed_label_id in label_ids:
            continue

        headers = msg.get("payload", {}).get("headers", [])
        sender = header_value(headers, "From")
        title  = header_value(headers, "Subject")
        snippet = msg.get("snippet","")

        slot, group, auto_archive, _usage = decide_eisenhower(cfg, title, sender, snippet)
        slot_label_name = cfg["eisenhower_labels"][slot]
        add_ids = [name_to_id[slot_label_name], processed_label_id]
        remove_ids = []

        if LOG_MASKING:
            print(f"[DECISION] '{head(title)}' from {mask_sender(sender)} => {slot.upper()} (group='{group}', auto_archive={auto_archive})")
        else:
            print(f"[DECISION] '{safe(title)}' from {safe(sender)} => {slot.upper()} (group='{group}', auto_archive={auto_archive})")

        if not DRY_RUN:
            modify_labels(svc, msg["id"], add=add_ids, remove=remove_ids)
            if auto_archive or slot == "q4":
                archive_message(svc, msg["id"])
                print("  -> archived (removed INBOX)")
        else:
            print("  -> DRY_RUN (no changes)")

        time.sleep(0.2)

if __name__ == "__main__":
    run()
