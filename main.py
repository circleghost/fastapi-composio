from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import httpx, os

app = FastAPI(title="Composio OAuth API (v3)")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
AUTH_CONFIG_ID   = os.getenv("AUTH_CONFIG_ID")
BASE_URL = "https://backend.composio.dev/api/v3"

def headers():
    if not COMPOSIO_API_KEY or not AUTH_CONFIG_ID:
        raise RuntimeError("缺少 COMPOSIO_API_KEY 或 AUTH_CONFIG_ID")
    return {"X-API-Key": COMPOSIO_API_KEY, "Content-Type": "application/json"}

@app.get("/", response_model=dict)
def root():
    return {"status": "ok", "api_version": "v3"}

@app.get("/oauth/success", response_class=HTMLResponse)
async def oauth_success(request: Request):
    return templates.TemplateResponse("oauth_success.html", {"request": request})

@app.post("/create-auth-link")
async def create_auth_link(
    user_id: str = Query(..., description="使用者 ID"),
    callback_url: str = Query(None, description="授權完成導回網址")
):
    if not callback_url:
        callback_url = "https://composio.zeabur.app/oauth/success"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1) 建立 connected account（v3 正確 payload）
            r = await client.post(
                f"{BASE_URL}/connected_accounts",
                headers=headers(),
                json={
                    "auth_config": { "id": AUTH_CONFIG_ID },
                    "connection": {
                        "entity": { "id": user_id },
                        "callback_url": callback_url
                    }
                }
            )
            if r.status_code not in (200, 201):
                raise HTTPException(status_code=r.status_code, detail=f"Composio API 錯誤: {r.text}")
            created = r.json()
            connection_id = created.get("id")
            redirect_url  = created.get("redirectUrl")

            # 2) 沒有即時回傳連結 → 先查詳情取 redirectUrl
            if not redirect_url:
                det = await client.get(
                    f"{BASE_URL}/connected_accounts/{connection_id}",
                    headers={"X-API-Key": COMPOSIO_API_KEY}
                )
                if det.status_code in (200, 201):
                    got = det.json()
                    redirect_url = got.get("redirectUrl")

            # 3) 仍然沒有 → 用公開端點補建 auth-link（v3）
            if not redirect_url:
                link = await client.post(
                    f"{BASE_URL}/connected_accounts/link",
                    headers=headers(),
                    json={
                        "connectionId": connection_id,
                        "callback_url": callback_url
                    }
                )
                if link.status_code not in (200, 201):
                    raise HTTPException(status_code=link.status_code, detail=f"Create auth-link 錯誤: {link.text}")
                payload = link.json()
                redirect_url = payload.get("url") or payload.get("redirectUrl")

            return {
                "success": True,
                "redirect_url": redirect_url,
                "connection_id": connection_id,
                "user_id": user_id
            }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"建立授權連結失敗: {str(e)}")

@app.get("/check-connection/{user_id}")
async def check_connection(user_id: str):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{BASE_URL}/connected_accounts",
                headers={"X-API-Key": COMPOSIO_API_KEY},
                params={"entityId": user_id}
            )
        if r.status_code != 200:
            return {"connected": False, "user_id": user_id}
        items = (r.json() or {}).get("items", []) or []
        for acc in items:
            if acc.get("status") == "ACTIVE":
                return {"connected": True, "account_id": acc.get("id"), "user_id": user_id}
        return {"connected": False, "user_id": user_id}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"檢查連線失敗: {str(e)}")
