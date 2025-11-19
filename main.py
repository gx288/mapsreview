import os
import json
import requests
from datetime import datetime

# Giữ nguyên 4 secrets cũ
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

def get_data_id_from_place():
    """Bước 1: Lấy data_id từ place_id (engine=google_maps theo docs)"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps",
        "type": "place",          # Theo docs: Để lấy chi tiết place
        "place_id": PLACE_ID,
        "hl": "vi",
        "gl": "vn",
        "api_key": SERPAPI_KEY
    }
    print(f"[{datetime.now()}] Bước 1: Lấy data_id từ Place ID {PLACE_ID[:20]}...")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    status = data.get("search_metadata", {}).get("status", "Unknown")
    print(f"SerpApi status (place): {status}")
    if status != "Success":
        print("Lỗi lấy data_id:", data.get("search_metadata", {}).get("error", "Unknown"))
        return None
    
    # Theo docs: data_id ở local_results[0].data_id hoặc place_results.data_id
    local_results = data.get("local_results", [])
    if local_results:
        data_id = local_results[0].get("data_id")
        title = local_results[0].get("title", "N/A")
        print(f"Quán từ SerpApi: {title} | Data ID: {data_id}")
        return data_id
    
    place_results = data.get("place_results", {})
    data_id = place_results.get("data_id")
    title = place_results.get("title", "N/A")
    print(f"Quán từ SerpApi: {title} | Data ID: {data_id}")
    return data_id

def get_reviews_from_data_id(data_id):
    """Bước 2: Lấy reviews từ data_id (engine=google_maps_reviews theo docs)"""
    if not data_id:
        print("Không có data_id – không lấy được reviews chi tiết.")
        return []
    
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps_reviews",
        "data_id": data_id,       # Theo docs: Bắt buộc dùng data_id
        "hl": "vi",
        "gl": "vn",
        "sort_by": "newestFirst",
        # ← BỎ num=20: Theo docs, không dùng trên initial page (sẽ lấy 8 mặc định)
        "api_key": SERPAPI_KEY
    }
    print(f"[{datetime.now()}] Bước 2: Lấy reviews từ Data ID {data_id[:20]}...")
    
    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        print(f"Lỗi từ reviews API: {response.status_code} - {response.text[:100]}")
        return []
    
    data = response.json()
    status = data.get("search_metadata", {}).get("status", "Unknown")
    print(f"SerpApi status (reviews): {status}")
    if status != "Success":
        print("Lỗi lấy reviews:", data.get("search_metadata", {}).get("error", "Unknown"))
        return []
    
    reviews = data.get("reviews", [])
    print(f"Tìm thấy {len(reviews)} reviews chi tiết (8 mặc định theo docs)")
    
    results = []
    for item in reviews:
        user = item.get("user", {})
        snippet = item.get("snippet", "")
        if item.get("extracted_snippet", {}).get("translated"):
            snippet = item.get("extracted_snippet", {}).get("translated", snippet)
        
        results.append({
            "review_id": item.get("review_id"),
            "author": user.get("name", "Ẩn danh"),
            "rating": item.get("rating"),
            "text": snippet,
            "time": item.get("date", "Không rõ")
        })
    
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
    
    data_id = get_data_id_from_place()
    current_reviews = get_reviews_from_data_id(data_id)
    
    if not current_reviews:
        print("Không lấy được reviews – kiểm tra quota SerpApi hoặc quán chưa có data_id.")
        return

    old_reviews = load_old_reviews()
    old_ids = {r.get("review_id", "") for r in old_reviews}

    new_reviews = [r for r in current_reviews if r.get("review_id", "") not in old_ids]

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

        all_reviews = current_reviews + [r for r in old_reviews if r.get("review_id", "") not in {x["review_id"] for x in current_reviews}]
        save_reviews(all_reviews[:300])
        print("→ Đã lưu dữ liệu mới vào reviews_data.json")
    else:
        print("Không có đánh giá mới.")

if __name__ == "__main__":
    main()
