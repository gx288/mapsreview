import os
import json
import requests
from datetime import datetime

# Secrets
PLACE_ID         = os.environ["PLACE_ID"]
SERPAPI_KEY      = os.environ["SERPAPI_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

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
        print(f"Lỗi đọc file data (sẽ tạo lại): {e}")
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
        "gl": "vn",  # THÊM DÒNG NÀY: Ưu tiên Việt Nam để lấy review địa phương
        "api_key": SERPAPI_KEY
    }
    print(f"Đang gọi SerpApi với Place ID: {PLACE_ID[:20]}...")  # Debug: in Place ID đầu
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    # DEBUG: In toàn bộ response để xem có gì
    print("SerpApi response keys:", list(data.keys()))
    print("Số lượng reviews:", len(data.get("reviews", [])))
    if "error" in data:
        print("Lỗi từ SerpApi:", data["error"])
    
    # In tên quán để xác nhận đúng
    title = data.get("title", "Không có tên")
    print(f"Tên quán từ SerpApi: {title}")
    
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
    except Exception as e:
        print("Lỗi gửi Telegram:", e)

def main():
    print(f"[{datetime.now()}] Đang kiểm tra đánh giá mới...")
    
    try:
        current_reviews = get_reviews()
        print(f"Lấy được {len(current_reviews)} đánh giá từ Google Maps")
    except Exception as e:
        print("Lỗi SerpApi:", e)
        return

    old_reviews = load_old_reviews()
    old_ids = {r["review_id"] for r in old_reviews if "review_id" in r}

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

        # Cập nhật data
        all_reviews = current_reviews + [r for r in old_reviews if r["review_id"] not in {x["review_id"] for x in current_reviews}]
        save_reviews(all_reviews[:300])
        print("Đã lưu dữ liệu mới vào reviews_data.json")
    else:
        print("Không có đánh giá mới.")

if __name__ == "__main__":
    main()
