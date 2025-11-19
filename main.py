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
        "engine": "google_maps_reviews",  # Theo docs: Engine chuyên reviews
        "place_id": PLACE_ID,             # Theo docs: Dùng Place ID (hoặc data_id)
        "hl": "vi",                       # Theo docs: Ngôn ngữ (vi cho tiếng Việt)
        "gl": "vn",                       # Theo docs: Localization (Việt Nam)
        "sort_by": "newestFirst",         # Theo docs: Sắp xếp mới nhất
        "num": 20,                        # Theo docs: Max 20 results
        "api_key": SERPAPI_KEY
    }
    print(f"[{datetime.now()}] Đang gọi SerpApi Reviews API với Place ID: {PLACE_ID[:20]}...")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    # Debug theo docs: Kiểm tra status và place_info (chỉ có ở page đầu)
    status_info = data.get("search_metadata", {})
    status = status_info.get("status", "Unknown")
    print(f"SerpApi status: {status}")
    if status != "Success":
        error_msg = status_info.get("error", "Unknown error")
        print(f"Lỗi SerpApi: {error_msg}")
        return []
    
    # Theo docs: In place_info để xác nhận (title, rating, reviews count)
    place_info = data.get("place_info", {})
    if place_info:
        title = place_info.get("title", "N/A")
        rating = place_info.get("rating", "N/A")
        total_reviews = place_info.get("reviews", "N/A")
        print(f"Quán: {title} | Rating: {rating} sao ({total_reviews} đánh giá tổng)")
    
    reviews = data.get("reviews", [])
    print(f"Tìm thấy {len(reviews)} reviews chi tiết (theo newestFirst)")
    
    results = []
    for item in reviews:
        # Theo docs: Fields chuẩn từ reviews array
        user = item.get("user", {})
        snippet = item.get("snippet", "")
        # Fallback cho translated snippet theo hl=vi
        if item.get("extracted_snippet", {}).get("translated"):
            snippet = item.get("extracted_snippet", {}).get("translated", snippet)
        
        results.append({
            "review_id": item.get("review_id"),  # Theo docs: review_id (unique)
            "author": user.get("name", "Ẩn danh"),  # Theo docs: user.name
            "rating": item.get("rating"),  # Theo docs: rating (float)
            "text": snippet,  # Theo docs: snippet hoặc extracted_snippet.translated
            "time": item.get("date", "Không rõ")  # Theo docs: date (human-readable)
        })
    
    # Sắp xếp mới nhất (dùng date nếu có, fallback time)
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
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("→ Đã gửi Telegram thành công!")
        else:
            print("Lỗi gửi Telegram:", response.text)
    except Exception as e:
        print("Lỗi gửi Telegram:", e)

def main():
    print(f"[{datetime.now()}] Bắt đầu kiểm tra đánh giá mới...")
    
    try:
        current_reviews = get_reviews()
        if not current_reviews:
            print("Không lấy được reviews – kiểm tra Place ID, SerpApi key hoặc quota.")
            return
    except Exception as e:
        print("Lỗi gọi API:", e)
        return

    old_reviews = load_old_reviews()
    old_ids = {r.get("review_id", "") for r in old_reviews}

    new_reviews = [r for r in current_reviews if r.get("review_id", "") not in old_ids]

    if new_reviews:
        print(f"Phát hiện {len(new_reviews)} đánh giá mới!")
        for rev in new_reviews[:10]:  # Theo docs: num=20, nhưng gửi max 10 để gọn Telegram
            stars = "⭐" * int(rev["rating"] or 0)
            msg = f"""
<b>ĐÁNH GIÁ MỚI – ĐÔNG Y SƠN HÀ</b>

<b>Người đánh giá:</b> {rev['author']}
<b>Điểm:</b> {rev['rating']} {stars}
<b>Thời gian:</b> {rev['time']}
<b>Nội dung:</b>
<i>{rev['text'] or '(Chỉ chấm sao, không nội dung)'}</i>

<a href="https://search.google.com/local/reviews?placeid={PLACE_ID}">Xem trên Maps</a>
            """.strip()
            send_to_telegram(msg)

        # Cập nhật data (giữ 300 cái gần nhất, theo docs không cần pagination cho lần đầu)
        all_reviews = current_reviews + [r for r in old_reviews if r.get("review_id", "") not in {x["review_id"] for x in current_reviews}]
        save_reviews(all_reviews[:300])
        print("→ Đã lưu dữ liệu mới vào reviews_data.json")
    else:
        print("Không có đánh giá mới.")

if __name__ == "__main__":
    main()
