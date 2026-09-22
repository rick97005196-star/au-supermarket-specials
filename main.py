import os
import threading
from typing import Optional, Dict, Any

# Load .env file if present
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database
from scrapers.updater import update_all_stores

app = FastAPI(title="澳洲超市每週特價追蹤器 (Woolworths / Coles / ALDI)")

from translator import translate_query

is_updating = False
update_progress = ""
update_lock = threading.Lock()

class ShoppingItemCreate(BaseModel):
    product_id: Optional[int] = None
    store: str
    title: str
    price: float = 0.0
    price_display: str = ""
    quantity: int = 1
    image_url: str = ""
    save_amount: float = 0.0

class ShoppingItemToggle(BaseModel):
    is_bought: bool

@app.on_event("startup")
def on_startup():
    database.init_db()

@app.get("/api/specials")
def api_get_specials(
    q: Optional[str] = None,
    store: Optional[str] = "All",
    period: Optional[str] = "current",
    discount_only: bool = False,
    category: Optional[str] = "All",
    sort_by: str = "relevance",
    limit: int = 150,
    offset: int = 0
):
    search_term = translate_query(q) if q else None
    return database.get_specials(
        query=search_term,
        store=store,
        period=period or "current",
        discount_only=discount_only,
        category=category,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )

@app.get("/api/stats")
def api_get_stats():
    return database.get_stats()

def run_update_task(pages: int):
    global is_updating, update_progress
    try:
        update_progress = "正在更新 Coles 特價..."
        update_all_stores(max_catalogue_pages=pages)
        update_progress = "更新完成！"
    except Exception as e:
        update_progress = f"更新失敗: {e}"
    finally:
        is_updating = False

@app.post("/api/update")
def api_trigger_update(background_tasks: BackgroundTasks, pages: int = 10):
    global is_updating, update_progress
    with update_lock:
        if is_updating:
            return {"status": "busy", "message": "目前已有更新作業正在執行中...", "progress": update_progress}
        is_updating = True
        update_progress = "開始爬取最新特價..."

    background_tasks.add_task(run_update_task, pages)
    return {"status": "started", "message": "已在背景啟動特價更新作業！"}

@app.get("/api/update-status")
def api_get_update_status():
    return {
        "is_updating": is_updating,
        "progress": update_progress
    }

# Shopping List Endpoints
@app.get("/api/shopping-list")
def api_get_shopping_list():
    items = database.get_shopping_list()
    # Group items by store
    grouped: Dict[str, list] = {'Woolworths': [], 'Coles': [], 'ALDI': [], 'Other': []}
    total_cost = 0.0
    total_saved = 0.0
    for item in items:
        st = item.get('store', 'Other')
        if st not in grouped:
            grouped[st] = []
        grouped[st].append(item)
        total_cost += (item.get('price', 0.0) or 0.0) * (item.get('quantity', 1) or 1)
        total_saved += (item.get('save_amount', 0.0) or 0.0) * (item.get('quantity', 1) or 1)

    return {
        "items": items,
        "grouped": grouped,
        "total_cost": round(total_cost, 2),
        "total_saved": round(total_saved, 2),
        "total_items": len(items)
    }

@app.post("/api/shopping-list")
def api_add_shopping_item(item: ShoppingItemCreate):
    new_id = database.add_to_shopping_list(item.dict())
    return {"id": new_id, "status": "created"}

@app.patch("/api/shopping-list/{item_id}")
def api_toggle_shopping_item(item_id: int, payload: ShoppingItemToggle):
    database.toggle_shopping_item(item_id, payload.is_bought)
    return {"status": "updated"}

@app.delete("/api/shopping-list/{item_id}")
def api_delete_shopping_item(item_id: int):
    database.delete_shopping_item(item_id)
    return {"status": "deleted"}

@app.delete("/api/shopping-list")
def api_clear_shopping_list(store: Optional[str] = None):
    database.clear_shopping_list(store)
    return {"status": "cleared"}

class EmailSendRequest(BaseModel):
    email: str
    items: list = []
    grouped: dict = {}
    total_cost: float = 0.0
    total_saved: float = 0.0
    text_content: str = ""
    html_content: str = ""

@app.post("/api/send-email")
def api_send_email(payload: EmailSendRequest):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "fallback": True,
            "message": "Local server: RESEND_API_KEY not configured. Falling back to email client."
        }
    try:
        import urllib.request
        import urllib.error
        import json
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps({
                "from": os.getenv("EMAIL_FROM", "AU Supermarket Specials <onboarding@resend.dev>"),
                "to": [payload.email],
                "subject": f"🛒 澳洲三大超市本週採買清單 (預估總額 ${payload.total_cost:.2f})",
                "text": payload.text_content,
                "html": payload.html_content
            }).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
            }
        )
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read().decode('utf-8')
            return {"ok": True, "message": "Email sent successfully via Resend", "data": json.loads(resp_data) if resp_data else {}}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = {"message": err_body}
        return {"ok": False, "fallback": True, "error": err_json}
    except Exception as e:
        return {"ok": False, "fallback": True, "error": str(e)}

# Serve Frontend static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Frontend static file index.html not found"}

@app.get("/{filename}")
def serve_root_file(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Not Found")

# Mount root static files so /app.js, /data/... work both locally and on Cloudflare Pages
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static_root")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
