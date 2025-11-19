import os
import json
import requests
from datetime import datetime

# Lấy từ GitHub Secrets
PLACE_ID           = os.environ["PLACE_ID"]
SERPAPI_KEY        = os.environ["SERPAPI_KEY"]
TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

DATA_FILE = "reviews_data.json"

def load_old_reviews():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_reviews(reviews):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

def get_reviews():
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps",
        "type": "place",
        "place_id": PLACE_ID,
        "hl": "vi",
        "api_key": SERPAPI_KEY
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    results = []
    for item in data.get("reviews", [])[:50]:
        results.append({
            "review_id": item.get("user_review_id") or f"{item.get('user',{}).get('id','')}_{item.get('date','')}",
            "author"   : item.get("user", {}).get("name", "Ẩn danh"),
            "rating"   : item.get("rating"),
            "text"     : item.get("snippet", ""),
            "time"     : item.get("date", "Không rõ thời gian")
        })
    return results

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def main():
    print(f"[{datetime.now()}] Đang kiểm tra đánh giá mới...")
    
    try:
        current_reviews = get_reviews()
    except Exception as e:
        print("Lỗi SerpApi:", e)
        return

    old_reviews = load_old_reviews()
    old_ids = {r["review_id"] for r in old_reviews}

    new_reviews = [r for r in current_reviews if r["review_id"] not in old_ids]

    if new_reviews:
        print(f"Phát hiện {len(new_reviews)} đánh giá mới!")
        for r in new_reviews[:10]:
            stars = "⭐" * int(r["rating"] or 0)
            msg = f"""
<b>Đánh giá mới trên Google Maps</b>

<b>Người đánh giá:</b> {r['author']}
<b>Điểm:</b> {r['rating']} {stars}
<b>Thời gian:</b> {r['time']}
<b>Nội dung:</b>
<i>{r['text'] or '(Chỉ đánh sao)'}</i>

<a href="https://search.google.com/local/reviews?placeid={PLACE_ID}">Xem trực tiếp</a>
            """.strip()
            send_telegram(msg)

        # Cập nhật file data
        all_reviews = current_reviews + [r for r in old_reviews if r["review_id"] not in {x["review_id"] for x in current_reviews}]
        save_reviews(all_reviews[:300])
    else:
        print("Không có đánh giá mới.")

if __name__ == "__main__":
    main()
