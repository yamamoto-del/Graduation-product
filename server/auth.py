"""
server/auth.py
PINコード認証ミドルウェア。
X-PIN ヘッダーを全リクエストで検証する。
/health エンドポイントのみ認証をスキップ。
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

# 認証をスキップするパス（完全一致）
_SKIP_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


class PinAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        pin = request.headers.get("X-PIN", "").strip()
        expected = str(settings.get("pin", "")).strip()

        if not expected:
            # PIN未設定時はすべて通す（初回セットアップ中）
            return await call_next(request)

        if pin != expected:
            return JSONResponse(
                status_code=401,
                content={"detail": "PIN が正しくありません。"},
            )

        return await call_next(request)
