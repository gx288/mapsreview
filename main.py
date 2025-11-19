import os, json, requests

SERPAPI_KEY      = os.environ["SERPAPI_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Data ID cố định của quán Đông y Sơn Hà
DATA_ID = "0x31360deb8469ea37:0x8fb9b82e13ac3823"

FILE = "reviews_data.json"

def load(): 
    return json.load(open(FILE,"r",encoding="utf-8")) if os.path.exists(FILE) else []

def save(data): 
    json.dump(data, open(FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def get_all_newest_reviews(max_reviews=50):
    all_reviews = []
    next_token = None
    
    while len(all_reviews) < max_reviews:
        params = {
            "engine": "google_maps_reviews",
            "data_id": DATA_ID,
            "hl": "vi",
            "gl": "vn",
            "sort_by": "newestFirst",
            "api_key": SERPAPI_KEY
        }
        if next_token:
            params["next_page_token"] = next_token
        
        print(f"Đang lấy trang tiếp theo... (đã có {len(all_reviews)} reviews)")
        data = requests.get("https://serpapi.com/search", params=params, timeout=40).json()
        
        if data.get("search_metadata", {}).get("status") != "Success":
            print("Lỗi SerpApi:", data.get("error"))
            break
            
        reviews = data.get("reviews", [])
        if not reviews:
            break
            
        for r in reviews:
            all_reviews.append({
                "id": r.get("review_id"),
                "author": r["user"].get("name", "Ẩn danh"),
                "rating": r.get("rating"),
                "text": r.get("snippet","") or r.get("extracted_snippet",{}).get("translated",""),
                "time": r.get("date", "Không rõ")
            })
        
        next_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if not next_token:
            break
    
    print(f"→ Tổng cộng lấy được {len(all_reviews)} reviews mới nhất")
    return all_reviews[:max_reviews]

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
                      timeout=10)
        print("→ Gửi Telegram OK")
    except:
        print("→ Lỗi gửi Telegram")

# ——————— MAIN ———————
current = get_all_newest_reviews(max_reviews=50)   # Có thể tăng lên 100 nếu muốn

if not current:
    print("Không lấy được dữ liệu")
else:
    old_ids = {r["id"] for r in load() if r.get("id")}
    new = [r for r in current if r["id"] not in old_ids]

    if new:
        print(f"→ PHÁT HIỆN {len(new)} ĐÁNH GIÁ MỚI!")
        for r in new[:10]:  # Gửi tối đa 10 cái mới nhất
            stars = "⭐" * int(r["rating"] or 0)
            msg = f"<b>ĐÁNH GIÁ MỚI – ĐÔNG Y SƠN HÀ</b>\n\n<b>{r['author']}</b>\n{r['rating']} {stars}\n{r['time']}\n<i>{r['text'] or 'Chỉ chấm sao'}</i>"
            send(msg)
        save(current)
    else:
        print("→ Không có đánh giá mới")
