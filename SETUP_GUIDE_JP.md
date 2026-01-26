# KakkyMailAnalyze セットアップガイド

ご友人や新しい環境でこのシステムを利用するための手順書です。

## 1. 必要なもの（APIキー等）
このシステムを動かすには、以下の4つの「鍵」が必要です。

1. **GMAIL_CLIENT_ID**
2. **GMAIL_CLIENT_SECRET**
3. **GMAIL_REFRESH_TOKEN**
4. **GEMINI_API_KEY**

---

## 2. APIキーの取得方法

### A. Gemini APIキーの取得（AI用）
1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセスします。
2. 「Create API key」をクリックして、発行されたキーを控えておきます。

### B. Gmail API 認証情報の取得（メールアクセス用）
少し手順が多いですが、最初の1回だけです。

1. **Google Cloud Console** にアクセス
   - [Google Cloud Console](https://console.cloud.google.com/) で新しいプロジェクトを作成します。
2. **Gmail API の有効化**
   - 「APIとサービス」 > 「ライブラリ」から「Gmail API」を検索し、「有効にする」を押します。
3. **OAuth 同意画面の設定**
   - 「OAuth 同意画面」で「外部」を選択し、最低限の情報を入力して作成します。
   - ※テストユーザーに自分のメールアドレスを追加するのを忘れないでください。
4. **認証情報の作成**
   - 「認証情報」 > 「認証情報を作成」 > 「OAuth クライアント ID」を選択。
   - アプリケーションの種類は **「デスクトップ アプリ」** を選択します。
   - ここで **GMAIL_CLIENT_ID** と **GMAIL_CLIENT_SECRET** が発行されます。

### C. リフレッシュトークンの取得
1. このリポジトリを自分のパソコンにダウンロード（git clone）します。
2. ターミナルで以下を実行して、必要なライブラリを入れます。
   ```bash
   pip install google-auth-oauthlib google-auth
   ```
3. 付属のスクリプトを実行します。
   ```bash
   python scripts/get_gmail_refresh_token.py
   ```
4. 画面の指示に従って ID と Secret を入力すると、ブラウザが開きます。自分のGoogleアカウントでログインして「許可」してください。
5. ターミナルの画面に **GMAIL_REFRESH_TOKEN** が表示されるので、これを控えます。

---

## 3. 実行の設定（GitHub Actions）
GitHubにこのコードをアップロード（Push）した後、以下の設定をします。

1. 自分のGitHubリポジトリの `Settings` > `Secrets and variables` > `Actions` を開きます。
2. **New repository secret** をクリックし、以下の4つをすべて登録します。
   - `GMAIL_CLIENT_ID`
   - `GMAIL_CLIENT_SECRET`
   - `GMAIL_REFRESH_TOKEN`
   - `GEMINI_API_KEY`

これで設定完了です！あとは自動で10分おきにメールが分類されます。
