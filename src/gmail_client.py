import os
from typing import Dict, List
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def make_credentials() -> Credentials:
    client_id = os.environ["GMAIL_CLIENT_ID"]
    client_secret = os.environ["GMAIL_CLIENT_SECRET"]
    refresh_token = os.environ["GMAIL_REFRESH_TOKEN"]
    return Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

def gmail_service():
    creds = make_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def list_messages(svc, query: str, max_results: int = 50):
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return resp.get("messages", [])

def get_message(svc, msg_id: str) -> Dict:
    return svc.users().messages().get(
        userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject", "To", "Date"]
    ).execute()

def ensure_labels(svc, names):
    existing = svc.users().labels().list(userId="me").execute().get("labels", [])
    name_to_id = {l["name"]: l["id"] for l in existing}
    for name in names:
        if name not in name_to_id:
            body = {"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
            created = svc.users().labels().create(userId="me", body=body).execute()
            name_to_id[name] = created["id"]
    return name_to_id

def modify_labels(svc, msg_id: str, add, remove):
    svc.users().messages().modify(
        userId="me", id=msg_id, body={"addLabelIds": add, "removeLabelIds": remove}
    ).execute()

def archive_message(svc, msg_id: str):
    modify_labels(svc, msg_id, add=[], remove=["INBOX"])
