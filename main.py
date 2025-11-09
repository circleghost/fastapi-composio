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

# 環境變數
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
AUTH_CONFIG_ID = os.getenv("AUTH_CONFIG_ID")

# 初始化 Composio
composio_client = Composio(api_key=COMPOSIO_API_KEY)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "Composio OAuth API",
        "endpoints": {
            "check_connection": "GET /check-connection/{user_id}",
            "create_auth_link": "POST /create-auth-link?user_id=xxx"
        }
    }

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(..., description="使用者 ID")):
    """為使用者建立 Google Sheets 授權連結"""
    try:
        # 注意：Composio SDK 使用 entity_id，不是 user_id
        connection_request = composio_client.connected_accounts.initiate(
            entity_id=user_id,  # ← 改成 entity_id
            auth_config_id=AUTH_CONFIG_ID
        )
        
        return {
            "success": True,
            "redirect_url": connection_request.redirectUrl,
            "connection_id": connection_request.id,
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
        # 注意：這裡也要改成 entity_ids
        accounts = composio_client.connected_accounts.list(
            entity_ids=[user_id]  # ← 改成 entity_ids
        )
        
        for account in accounts.items:
            if account.status == "ACTIVE":
                return {
                    "connected": True,
                    "account_id": account.id,
                    "user_id": user_id
                }
        
        return {
            "connected": False,
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"檢查連線失敗: {str(e)}"
        )

@app.get("/health")
def health_check():
    return {"status": "healthy"}
