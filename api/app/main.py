from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI(title="AI Workflow API", version="0.1.0")

# Optional CORS (not needed if UI is same-origin via /api path routing)
ui_origin = os.getenv("UI_ORIGIN")
if ui_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ui_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

class PingResponse(BaseModel):
    ok: bool
    message: str


def get_current_token(authorization: str | None = Header(default=None)):
    # Minimal placeholder auth: accept Authorization: Bearer dev (for demo only)
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    if token != "dev":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"sub": "demo-user"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ping", response_model=PingResponse)
async def ping():
    return PingResponse(ok=True, message="pong")


@app.get("/api/secure")
async def secure_claims(user=Depends(get_current_token)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return {"ok": True, "user": user}
