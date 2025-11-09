from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx, os

app = FastAPI(title="Composio OAuth API (v3)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")   # 必填：Composio API Key
AUTH_CONFIG_ID   = os.getenv("AUTH_CONFIG_ID")     # 必填：ac_ 開頭的 Auth Config ID
BASE_URL = "https://backend.composio.dev/api/v3"   # v3 前綴

def headers():
    if not COMPOSIO_API_KEY or not AUTH_CONFIG_ID:
        raise RuntimeError("環境變數缺少 COMPOSIO_API_KEY 或 AUTH_CONFIG_ID")
    return {"X-API-Key": COMPOSIO_API_KEY, "Content-Type": "application/json"}

@app.get("/")
def root():
    return {"status": "ok", "api_version": "v3"}

@app.post("/create-auth-link")
async def create_auth_link(
    user_id: str = Query(..., description="你的使用者 ID（例如 LINE User ID）"),
    callback_url: str = Query("https://your-app.com/oauth/success", description="授權完成後導回的網址")
):
    """
    1) 建立 Connected Account（把 user_id 綁到 connection.entity.id）
    2) 若未回傳 redirectUrl，補呼叫 auth_sessions 產生 OAuth 登入連結
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1) v3：建立 connected account（正確欄位：auth_config + connection.entity.id）
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

            # 2) 若沒有登入 URL → 建立 auth‑link session（公開端點）
            if not redirect_url:
                link = await client.post(
                    f"{BASE_URL}/auth_sessions",
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
    """
    依 entityId 查詢該使用者是否已授權（ACTIVE） 
    """
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
