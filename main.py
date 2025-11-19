import os
import json
import requests
from datetime import datetime
import urllib.parse

# Secrets (thêm GOOGLE_PLACES_KEY mới)
GOOGLE_PLACES_KEY = os.environ["GOOGLE_PLACES_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PLACE_ID         = os.environ["PLACE_ID"]

DATA_FILE = "reviews_data.json"

def load_old_reviews():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, PermissionError, OSError) as e:
        print(f"Lỗi đọc file data: {e}")
        return []

def save_reviews(reviews):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

def get_reviews():
    # Lấy reviews từ Google Places API
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": PLACE_ID,
        "fields": "name,rating,reviews,user_ratings_total",  # Lấy reviews + tổng
        "language": "vi",
        "key": GOOGLE_PLACES_KEY
    }
    print(f"Đang gọi Google Places API với Place ID: {PLACE_ID[:20]}...")
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    print("Google API status:", data.get("status"))
    print("Tên quán:", data.get("result", {}).get("name", "N/A"))
    print("Rating tổng:", data.get("result", {}).get("rating"), f"({data.get('result', {}).get('user_ratings_total', 0)} đánh giá)")
    
    results = []
    reviews = data.get("result", {}).get("reviews", [])
    print(f"Tìm thấy {len(reviews)} reviews chi tiết")
    
    for item in reviews[:20]:  # Lấy tối đa 20 (Google giới hạn 5 mặc định, nhưng fields=reviews lấy 5; nếu cần nhiều hơn, dùng pagetoken)
        results.append({
            "review_id": item.get("time", 0),  # Dùng timestamp làm ID
            "author": item.get("author_name", "Ẩn danh"),
            "rating": item.get("rating"),
            "text": item.get("text", ""),
            "time": item.get("relative_time_description", "Không rõ")  # e.g., "2 tuần trước"
        })
    
    results.sort(key=lambda x: x.get("time", ""), reverse=True)
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
        print("Gửi Telegram thành công!")
    except Exception as e:
        print("Lỗi Telegram:", e)

def main():
    print(f"[{datetime.now()}] Kiểm tra đánh giá mới...")
    
    try:
        current_reviews = get_reviews()
        print(f"Lấy được {len(current_reviews)} đánh giá chi tiết")
    except Exception as e:
        print("Lỗi Google API:", e)
        return

    old_reviews = load_old_reviews()
    old_ids = {r["review_id"] for r in old_reviews if "review_id" in r}

    new_reviews = [r for r in current_reviews if r["review_id"] not in old_ids]

    if new_reviews:
        print(f"Phát hiện {len(new_reviews)} đánh giá mới!")
        for r in new_reviews[:10]:
            stars = "⭐" * int(r["rating"] or 0)
            msg = f"""
<b>Đánh giá mới trên Google Maps!</b>

<b>Tác giả:</b> {r['author']}
<b>Điểm:</b> {r['rating']} {stars}
<b>Thời gian:</b> {r['time']}
<b>Nội dung:</b> <i>{r['text'] or '(Chỉ đánh sao)'}</i>

<a href="https://search.google.com/local/reviews?placeid={PLACE_ID}">Xem trên Maps</a>
            """.strip()
            send_telegram(msg)

        # Cập nhật data
        all_reviews = current_reviews + [r for r in old_reviews if r["review_id"] not in {x["review_id"] for x in current_reviews}]
        save_reviews(all_reviews[:300])
        print("Đã lưu dữ liệu mới!")
    else:
        print("Không có đánh giá mới.")

if __name__ == "__main__":
    main()
