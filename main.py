import os, json, requests
from datetime import datetime

SERPAPI_KEY    = os.environ["SERPAPI_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID        = os.environ["TELEGRAM_CHAT_ID"]
PLACE_ID       = os.environ["PLACE_ID"]
FILE           = "reviews_data.json"

def load(): 
    return json.load(open(FILE,"r",encoding="utf-8")) if os.path.exists(FILE) else []

def save(data): 
    json.dump(data, open(FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def get_reviews():
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_maps_reviews",      # ← Dùng endpoint chuyên reviews
        "place_id": PLACE_ID,
        "hl": "vi",
        "gl": "vn",
        "api_key": SERPAPI_KEY
    }
    data = requests.get(url, params=params, timeout=60).json()
    reviews = data.get("reviews", [])
    print(f"→ Lấy được {len(reviews)} reviews")
    return [{
        "id": r.get("review_id") or f"{r['user']['id']}_{r['time']['iso_date']}",
        "author": r["user"]["name"],
        "rating": r["rating"],
        "text": r.get("snippet",""),
        "time": r["time"]["iso_date"][:10]
    } for r in reviews]

def send(msg):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

current = get_reviews()
old_ids = {r["id"] for r in load()}
new = [r for r in current if r["id"] not in old_ids]

if new:
    print(f"→ Có {len(new)} đánh giá mới!")
    for r in new[:5]:
        send(f"<b>ĐÁNH GIÁ MỚI</b>\n\n<b>{r['author']}</b>\n{r['rating']} ⭐\n{r['time']}\n<i>{r['text'] or 'Chỉ chấm sao'}</i>")
    save(current)
else:
    print("→ Không có đánh giá mới")

# Phần commit push giữ nguyên như cũ của bạn là được
