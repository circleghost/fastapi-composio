from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from composio import Composio
import os

app = FastAPI(title="Composio OAuth API")
templates = Jinja2Templates(directory="templates")

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

# 初始化 Composio SDK
composio_client = Composio(api_key=COMPOSIO_API_KEY)

@app.get("/")
def root():
    return {"status": "ok", "service": "Composio OAuth API"}

@app.get("/oauth/success", response_class=HTMLResponse)
async def oauth_success(request: Request):
    return templates.TemplateResponse("oauth_success.html", {"request": request})

@app.post("/create-auth-link")
async def create_auth_link(
    user_id: str = Query(..., description="使用者 ID"),
    callback_url: str = Query(None, description="授權完成後導回的網址")
):
    """
    使用 Composio SDK 的 ConnectedAccounts.link() 建立授權連結
    根據官方文件：https://docs.composio.dev/sdk/python/connected_accounts#link
    """
    if not callback_url:
        callback_url = "https://composio.zeabur.app/oauth/success"
    
    try:
        # 使用 SDK 的 link() 方法建立授權連結
        connection_request = composio_client.connected_accounts.link(
            user_id=user_id,
            auth_config_id=AUTH_CONFIG_ID,
            callback_url=callback_url
        )
        
        return {
            "success": True,
            "redirect_url": connection_request.redirectUrl,
            "connection_id": connection_request.id,
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立授權連結失敗: {str(e)}")

@app.get("/check-connection/{user_id}")
async def check_connection(user_id: str):
    """
    檢查使用者是否已授權
    """
    try:
        # 使用 SDK 列出該使用者的 connected accounts
        accounts = composio_client.connected_accounts.list(user_id=user_id)
        
        # 檢查是否有 ACTIVE 狀態的帳號
        for account in accounts.items:
            if account.status == "ACTIVE":
                return {
                    "connected": True,
                    "account_id": account.id,
                    "user_id": user_id
                }
        
        return {"connected": False, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檢查連線失敗: {str(e)}")
