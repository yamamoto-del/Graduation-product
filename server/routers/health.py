"""
server/routers/health.py
GET /health  —  サーバー・弥生販売の稼働確認。
PIN認証をスキップするエンドポイント。
"""

import psutil
from fastapi import APIRouter

from ..config import settings
from ..database import get_db
from ..models import HealthResponse

router = APIRouter()


def _check_yayoi() -> tuple[bool, str]:
    """弥生販売 26 が起動しているか確認する。"""
    keyword = settings.get("yayoi_exe_name", "販売26")
    try:
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                name = proc.info.get("name") or ""
                exe  = proc.info.get("exe")  or ""
                if keyword in name or keyword in exe:
                    return True, f"弥生販売 26（PID: {proc.pid}）"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False, "起動していません"


def _check_db() -> bool:
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    yayoi_running, yayoi_version = _check_yayoi()
    db_ok = _check_db()
    status = "ok" if (db_ok and yayoi_running) else "degraded"
    return HealthResponse(
        status=status,
        yayoi_running=yayoi_running,
        yayoi_version=yayoi_version,
        db_ok=db_ok,
    )
