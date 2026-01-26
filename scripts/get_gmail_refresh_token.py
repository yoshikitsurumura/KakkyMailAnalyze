# Obtain a Gmail OAuth refresh token locally (run once).
# Usage:
#   pip install google-auth-oauthlib google-auth
#   python scripts/get_gmail_refresh_token.py
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def main():
    client_id = os.environ.get("GMAIL_CLIENT_ID") or input("GMAIL_CLIENT_ID: ").strip()
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET") or input("GMAIL_CLIENT_SECRET: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    print("\n=== SAVE THIS REFRESH TOKEN TO GITHUB SECRETS ===")
    print(creds.refresh_token)

if __name__ == "__main__":
    main()
