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
    for entry in feed.entries:
        title = entry.title
        link = entry.link
        pub_date = entry.get("published", "")  # 出版日がない場合は空文字
        media = "RSS"  # ここは必要に応じて entry.source.title 等に変更可能

        if link in existing_urls:
            continue  # 重複判定

        # Geminiで要約取得
        summary = summarize_with_gemini(title, link)
        
        # スプレッドシートのカラム順（B, F, E, A, D, C, G）に合わせる
        # ここでは、例として次のように入れる：
        #   - B列: タイトル
        #   - F列: （キーワード・タグ、ここは空）
        #   - E列: 要約
        #   - A列: 日付（pub_date）
        #   - D列: 媒体（media）
        #   - C列: URL
        #   - G列: 収集元（"RSS"）
        row = [pub_date, title, link, media, summary, "", "RSS"]
        # ただし、あなたの既存のレイアウトが「B→F→E→A→D→C→G」なら
        # それに合わせるために順序を調整してください。
        # 以下は一例です。必要に応じて調整してください。
        # 例えば、もし B列にタイトル、F列が空欄、E列が要約、
        # A列に日付、D列に媒体、C列にURL、G列に収集元なら：
        row_final = [pub_date, title, link, media, summary, "", "RSS"]
        
        sheet.append_row(row_final, value_input_option="USER_ENTERED")
        new_count += 1

print(f"{new_count} 件の新しい記事を追加しました。")

