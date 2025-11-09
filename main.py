from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="Composio OAuth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
BASE_URL = "https://backend.composio.dev/api/v1"

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "Composio OAuth API",
        "version": "3.0.0"
    }

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(..., description="使用者 ID")):
    """為使用者建立 Google Sheets 授權連結"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/connectedAccounts",
                headers={
                    "X-API-Key": COMPOSIO_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "integrationId": "googlesheets",
                    "userUuid": user_id
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Composio API 錯誤: {response.text}"
                )
            
            data = response.json()
            return {
                "success": True,
                "redirect_url": data.get("redirectUrl"),
                "connection_id": data.get("id"),
                "user_id": user_id
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"建立授權連結失敗: {str(e)}"
        )

@app.get("/check-connection/{user_id}")
async def check_connection(user_id: str):
    """檢查使用者是否已授權 Google Sheets"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/connectedAccounts",
                headers={
                    "X-API-Key": COMPOSIO_API_KEY
                },
                params={
                    "user_uuid": user_id
                }
            )
            
            if response.status_code != 200:
                return {"connected": False, "user_id": user_id}
            
            data = response.json()
            items = data.get("items", [])
            
            for account in items:
                if account.get("status") == "ACTIVE":
                    return {
                        "connected": True,
                        "account_id": account.get("id"),
                        "user_id": user_id
                    }
            
            return {"connected": False, "user_id": user_id}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"檢查連線失敗: {str(e)}"
        )

@app.get("/health")
def health_check():
    return {"status": "healthy"}
