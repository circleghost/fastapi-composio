from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from composio import Composio
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
AUTH_CONFIG_ID = os.getenv("AUTH_CONFIG_ID")

composio_client = Composio(api_key=COMPOSIO_API_KEY)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Composio OAuth API"}

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(...)):
    """為使用者建立 Google Sheets 授權連結"""
    try:
        # 方法 1: 嘗試使用 create_connected_account (新版 API)
        try:
            connection_request = composio_client.create_connected_account(
                user_id=user_id,
                integration=AUTH_CONFIG_ID
            )
        except AttributeError:
            # 方法 2: 如果沒有 create_connected_account，使用舊版 API
            connection_request = composio_client.connected_accounts.create(
                entity_id=user_id,
                integration_id=AUTH_CONFIG_ID
            )
        
        return {
            "success": True,
            "redirect_url": connection_request.redirectUrl,
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"錯誤: {str(e)}")

@app.get("/check-connection/{user_id}")
async def check_connection(user_id: str):
    """檢查使用者是否已授權"""
    try:
        accounts = composio_client.connected_accounts.list(entity_id=user_id)
        
        for account in accounts:
            if hasattr(account, 'status') and account.status == "ACTIVE":
                return {"connected": True, "account_id": account.id}
        
        return {"connected": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"錯誤: {str(e)}")
