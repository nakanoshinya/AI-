import feedparser
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# --- 認証 ---
cred_json = os.environ['GOOGLE_SHEET_CREDENTIALS']
cred_data = json.loads(cred_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_data, scope)
client = gspread.authorize(creds)

sheet = client.open("URL自動").sheet1  # スプレッドシート名をここで指定

# --- 既存URLを取得（重複防止） ---
existing_urls = sheet.col_values(6)  # C列 = URL列

# --- RSSフィード一覧 ---
rss_feeds = {
    "Googleニュース（生成AI）": "https://news.google.com/rss/search?q=生成AI&hl=ja&gl=JP&ceid=JP:ja",
    "The Decoder": "https://the-decoder.com/feed/",
    "TechCrunch（AI）": "https://techcrunch.com/tag/generative-ai/feed/"
}

new_entries = []

for source, url in rss_feeds.items():
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = entry.title
        link = entry.link
        pub_date = entry.get("published", datetime.now().strftime("%Y-%m-%d"))
        media = source

        if link in existing_urls:
            continue

        # [B, F, E, A, D, C, G]
        row = [title, "", "", pub_date, media, link, "RSS"]
        new_entries.append(row)

if new_entries:
    sheet.append_rows(new_entries, value_input_option="USER_ENTERED")
    print(f"{len(new_entries)} 件の新しい記事を追加しました。")
else:
    print("新しい記事はありませんでした。")
