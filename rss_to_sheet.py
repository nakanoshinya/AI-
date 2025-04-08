import os
import feedparser
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- 環境変数から認証情報を取得 ---
cred_json = os.environ["GOOGLE_SHEET_CREDENTIALS"]
import json
creds_dict = json.loads(cred_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# --- Gemini APIキー設定 ---
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# --- 要約関数 ---

def summarize_with_gemini(title, url):
    prompt = f"以下の記事の内容を要約してください：\n\nタイトル：{title}\nURL：{url}"
    model = genai.GenerativeModel("gemini-pro")
    try:
        response = model.generate_content(prompt)
        
        # --- レスポンスの中身に応じて取得 ---
        if hasattr(response, "text"):
            return response.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            return response.candidates[0].content.parts[0].text.strip()
        else:
            return "[要約失敗] 要約レスポンスの構造を解析できませんでした。"
    
    except Exception as e:
        return f"[要約失敗] {e}"



# --- RSSフィード一覧（必要に応じて変更） ---
rss_urls = [
    "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "https://gigazine.net/news/rss_2.0/",
    "https://www.itmedia.co.jp/rss/2.0/news_bursts.xml"
]

# --- スプレッドシート設定 ---
sheet = client.open("URL自動").sheet1

# --- 既存URLの取得（重複チェック用） ---
existing_urls = [row[5] for row in sheet.get_all_values()[1:] if len(row) > 5]

# --- RSS処理開始 ---
new_count = 0
for url in rss_urls:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = entry.title
        link = entry.link
        pub_date = entry.published if "published" in entry else ""
        media = entry.get("source", {}).get("title", "RSS")

        if link in existing_urls:
            continue

        # 要約実行
        summary = summarize_with_gemini(title, link)

        # B:タイトル, F:キーワード, E:要約, A:日付, D:媒体, C:URL, G:収集元
        row = [pub_date, media, link, title, summary, "", "RSS"]
        sheet.append_row(row)
        new_count += 1

print(f"{new_count} 件の新しい記事を追加しました。")
