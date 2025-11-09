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

# 初始化 Composio
composio_client = Composio(api_key=COMPOSIO_API_KEY)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "Composio OAuth API",
        "version": "1.0.0"
    }

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(..., description="使用者 ID")):
    """為使用者建立 Google Sheets 授權連結"""
    try:
        # 正確的參數：user_id（不是 entity_id）
        # 不需要 auth_config_id，改用 integration_id
        connection_request = composio_client.connected_accounts.initiate(
            user_id=user_id,
            integration_id="googlesheets"  # 直接用 integration_id
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
        # list() 方法使用 user_id 參數（單數）
        accounts = composio_client.connected_accounts.list(
            user_id=user_id
        )
        
        # 檢查是否有 ACTIVE 狀態的帳號
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
