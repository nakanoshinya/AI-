import os
import feedparser
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json

# --- 認証情報の取得 ---
# 環境変数 GOOGLE_SHEET_CREDENTIALS に認証情報のJSON文字列が設定されている前提
cred_json = os.environ["GOOGLE_SHEET_CREDENTIALS"]
creds_dict = json.loads(cred_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("URL自動").sheet1

# --- Gemini APIキー設定 ---
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# --- 要約関数（改良版） ---
def summarize_with_gemini(title, url):
    """
    Gemini API を用いて、タイトルとURLから記事の要約を自動で取得する関数。
    レスポンスに応じて複数の属性をチェックし、要約テキストを抽出する。
    失敗した場合は、詳細なエラーメッセージを返す。
    """
    prompt = f"以下の記事の内容を要約してください：\n\nタイトル：{title}\nURL：{url}"
    model = genai.GenerativeModel("gemini-pro")
    try:
        response = model.generate_content(prompt)
        print("[DEBUG] Gemini response:", response)
        
        if hasattr(response, "text") and response.text and response.text.strip():
            return response.text.strip()
        elif hasattr(response, "parts") and response.parts:
            first_part = response.parts[0]
            if hasattr(first_part, "text") and first_part.text.strip():
                return first_part.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts") and candidate.content.parts:
                first_part = candidate.content.parts[0]
                if hasattr(first_part, "text") and first_part.text.strip():
                    return first_part.text.strip()
        return "[要約失敗] Geminiレスポンスから有効な要約テキストが取得できませんでした。"
    
    except Exception as e:
        return f"[要約失敗] Gemini APIエラー: {str(e)}"

# --- RSSフィード一覧（例：適宜変更してください） ---
rss_urls = [
    "https://news.google.com/rss/search?q=生成AI&hl=ja&gl=JP&ceid=JP:ja",
    "https://the-decoder.com/feed/",
    "https://techcrunch.com/tag/generative-ai/feed/"
]

# --- 既存URLの取得（重複チェック） ---
rows = sheet.get_all_values()
existing_urls = [row[5] for row in rows[1:] if len(row) > 5]  # C列

new_count = 0

# --- RSS処理開始 ---
for rss_url in rss_urls:
    feed = feedparser.parse(rss_url)
    # --- バッチ更新用のリストを準備 ---
rows_to_append = []

for rss_url in rss_urls:
    feed = feedparser.parse(rss_url)
    for entry in feed.entries:
        title = entry.title
        link = entry.link
        pub_date = entry.get("published", "")
        media = "RSS"
        
        if link in existing_urls:
            continue  # 重複はスキップ
        
        # Geminiで要約取得
        summary = summarize_with_gemini(title, link)
        
        # あなたのスプレッドシートのカラム順（B→F→E→A→D→C→G）に合わせる例：
        # ※実際の並びに合わせて適宜調整してください
        row_final = [pub_date, title, link, media, summary, "", "RSS"]
        rows_to_append.append(row_final)

# 追加する行がある場合、一度に追加
if rows_to_append:
    sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
    print(f"{len(rows_to_append)} 件の新しい記事を一括追加しました。")
else:
    print("新しい記事はありませんでした。")

print(f"[LOG] 全RSSフィード数: {len(rss_urls)}")

for rss_url in rss_urls:
    print(f"[LOG] 処理中のRSS: {rss_url}")
    feed = feedparser.parse(rss_url)
    print(f"[LOG] 記事数: {len(feed.entries)}")

    for entry in feed.entries:
        title = entry.title
        link = entry.link
        print(f"[LOG] 処理中のタイトル: {title}")
        print(f"[LOG] URL: {link}")

        if link in existing_urls:
            print("[SKIP] 重複URLなのでスキップ")
            continue

        summary = summarize_with_gemini(title, link)
        print(f"[LOG] 要約: {summary[:50]}...")  # 要約の冒頭だけ

        row_final = [pub_date, title, link, media, summary, "", "RSS"]
        rows_to_append.append(row_final)

print(f"[RESULT] 書き込む行数: {len(rows_to_append)}")

