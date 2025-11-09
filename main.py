from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="Composio OAuth API (v3)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")  # 放你的 Composio API Key
AUTH_CONFIG_ID   = os.getenv("AUTH_CONFIG_ID")    # 放 ac_ 開頭的 Auth Config ID
BASE_URL = "https://backend.composio.dev/api/v3"  # v3 前綴

@app.get("/")
def root():
    return {"status": "ok", "api_version": "v3"}

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(..., description="你的使用者 ID")):
    """
    建立 Google Sheets 授權連結（v3：POST /connected_accounts）
    Body 需要包含：
      - auth_config: { id: "ac_xxxx" }
      - connection: { entity: { id: "<user_id>" }, callback_url?: "<your-url>" }
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{BASE_URL}/connected_accounts",
                headers={
                    "X-API-Key": COMPOSIO_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "auth_config": { "id": AUTH_CONFIG_ID },
                    "connection": {
                        "entity": { "id": user_id },
                        # 可選：授權後導回頁（不需要可刪）
                        "callback_url": "https://your-app.com/oauth/success"
                    }
                }
            )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=f"Composio API 錯誤: {r.text}")
        data = r.json()
        return {
            "success": True,
            "redirect_url": data.get("redirectUrl"),
            "connection_id": data.get("id"),
            "user_id": user_id
        }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"建立授權連結失敗: {str(e)}")

@app.get("/check-connection/{user_id}")
async def check_connection(user_id: str):
    """
    檢查該使用者是否已有有效的 Connected Account
    v3：GET /connected_accounts?entityId=<user_id>
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{BASE_URL}/connected_accounts",
                headers={ "X-API-Key": COMPOSIO_API_KEY },
                params={ "entityId": user_id }
            )
        if r.status_code != 200:
            return {"connected": False, "user_id": user_id}
        data = r.json()
        items = data.get("items", []) or []
        for acc in items:
            if acc.get("status") == "ACTIVE":
                return {
                    "connected": True,
                    "account_id": acc.get("id"),
                    "user_id": user_id
                }
        return {"connected": False, "user_id": user_id}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"檢查連線失敗: {str(e)}")
