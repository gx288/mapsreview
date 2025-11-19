import os
import json
import requests
from datetime import datetime

# Giữ nguyên 4 secrets cũ của bạn
SERPAPI_KEY      = os.environ["SERPAPI_KEY"]
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
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps_reviews",  # ← FIX THEO DOCS: Engine chuyên reviews
        "place_id": PLACE_ID,             # ← Trực tiếp dùng Place ID
        "hl": "vi",                       # Tiếng Việt
        "gl": "vn",                       # Việt Nam
        "sort_by": "newestFirst",         # ← Sắp xếp mới nhất (theo docs)
        "num": 20,                        # Lấy tối đa 20 (theo docs)
        "api_key": SERPAPI_KEY
    }
    print(f"Đang gọi SerpApi Reviews API với Place ID: {PLACE_ID[:20]}...")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    # Debug theo docs: Kiểm tra status và keys
    status = data.get("search_metadata", {}).get("status", "Unknown")
    print(f"SerpApi status: {status}")
    if status != "Success":
        print("Lỗi SerpApi:", data.get("search_metadata", {}).get("error", "Unknown error"))
        return []
    
    reviews = data.get("reviews", [])
    print(f"Tìm thấy {len(reviews)} reviews chi tiết")
    
    results = []
    for item in reviews:
        # Theo docs: Các field chuẩn
        user = item.get("user", {})
        results.append({
            "review_id": item.get("review_id") or f"{user.get('id', '')}_{item.get('date', '')}",
            "author": user.get("name", "Ẩn danh"),
            "rating": item.get("rating"),
            "text": item.get("snippet", ""),
            "time": item.get("date", "Không rõ thời gian")  # Human-readable date theo docs
        })
    
    # Sắp xếp mới nhất (dùng time nếu có)
    results.sort(key=lambda x: x.get("time", ""), reverse=True)
    return results

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
        print("→ Đã gửi Telegram thành công!")
    except Exception as e:
        print("Lỗi gửi Telegram:", e)

def main():
    print(f"[{datetime.now()}] Đang kiểm tra đánh giá mới...")
    
    try:
        current_reviews = get_reviews()
        if not current_reviews:
            print("Không lấy được reviews – kiểm tra Place ID hoặc SerpApi key.")
            return
    except Exception as e:
        print("Lỗi gọi API:", e)
        return

    old_reviews = load_old_reviews()
    old_ids = {r["review_id"] for r in old_reviews if "review_id" in r}

    new_reviews = [r for r in current_reviews if r["review_id"] not in old_ids]

    if new_reviews:
        print(f"Phát hiện {len(new_reviews)} đánh giá mới!")
        for rev in new_reviews[:10]:
            stars = "⭐" * int(rev["rating"] or 0)
            msg = f"""
<b>ĐÁNH GIÁ MỚI – ĐÔNG Y SƠN HÀ</b>

<b>Người đánh giá:</b> {rev['author']}
<b>Điểm:</b> {rev['rating']} {stars}
<b>Thời gian:</b> {rev['time']}
<b>Nội dung:</b>
<i>{rev['text'] or '(Chỉ chấm sao)'}</i>

<a href="https://search.google.com/local/reviews?placeid={PLACE_ID}">Xem trên Maps</a>
            """.strip()
            send_to_telegram(msg)

        # Cập nhật data (giữ 300 cái gần nhất)
        all_reviews = current_reviews + [r for r in old_reviews if r["review_id"] not in {x["review_id"] for x in current_reviews}]
        save_reviews(all_reviews[:300])
        print("→ Đã lưu dữ liệu mới vào reviews_data.json")
    else:
        print("Không có đánh giá mới.")

if __name__ == "__main__":
    main()
