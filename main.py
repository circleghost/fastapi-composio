from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from composio import Composio
import os

app = FastAPI(title="Composio OAuth API")

# CORS 設定
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

# 初始化
composio_client = Composio(api_key=COMPOSIO_API_KEY)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Composio API"}

@app.post("/create-auth-link")
async def create_auth_link(user_id: str = Query(...)):
    try:
        connection_request = composio_client.connected_accounts.initiate(
            user_id=user_id,
            auth_config_id=AUTH_CONFIG_ID
        )
        return {
            "success": True,
            "redirect_url": connection_request.redirectUrl
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-connection/{user_id}")
async def check_connection(user_id: str):
    try:
        accounts = composio_client.connected_accounts.list(user_ids=[user_id])
        for account in accounts.items:
            if account.status == "ACTIVE":
                return {"connected": True, "account_id": account.id}
        return {"connected": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
