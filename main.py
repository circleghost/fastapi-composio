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

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
AUTH_CONFIG_ID   = os.getenv("AUTH_CONFIG_ID")  # ac_ 開頭
BASE_URL = "https://backend.composio.dev/api/v3"

def headers():
    return {"X-API-Key": COMPOSIO_API_KEY, "Content-Type": "application/json"}

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1) 建立 connected account
            r = await client.post(
                f"{BASE_URL}/connected_accounts",
                headers=headers(),
                json={
                    "auth_config": { "id": AUTH_CONFIG_ID },
                    "connection": {
                        "entity": { "id": user_id },
                        "callback_url": "https://your-app.com/oauth/success"
                    }
                }
            )
            if r.status_code not in (200, 201):
                raise HTTPException(status_code=r.status_code, detail=f"Composio API 錯誤: {r.text}")
            data = r.json()
            connection_id = data.get("id")
            redirect_url = data.get("redirectUrl")

            # 2) 若未給 redirectUrl，建立 auth-link session 拿登入 URL
            if not redirect_url:
                lr = await client.post(
                    f"{BASE_URL}/internal/connected_accounts/link",
                    headers=headers(),
                    json={
                        "connectionId": connection_id,
                        "callback_url": "https://your-app.com/oauth/success"
                    }
                )
                if lr.status_code not in (200, 201):
                    raise HTTPException(status_code=lr.status_code, detail=f"Create auth-link 錯誤: {lr.text}")
                link_payload = lr.json()
                # 文件常見回傳包含 url 或 token（若是 token，後端會提供可直接導向的 URL） 
                redirect_url = link_payload.get("url") or link_payload.get("redirectUrl")

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
        items = (r.json() or {}).get("items", [])
        for acc in items:
            if acc.get("status") == "ACTIVE":
                return {"connected": True, "account_id": acc.get("id"), "user_id": user_id}
        return {"connected": False, "user_id": user_id}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"檢查連線失敗: {str(e)}")
