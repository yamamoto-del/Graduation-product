"""
server/main.py
FastAPI サーバー エントリポイント。

起動方法:
    cd server
    uvicorn main:app --host 0.0.0.0 --port 8765 --reload

PCのIPアドレスを固定した後、スマホアプリから http://<PC_IP>:8765 に接続する。
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import PinAuthMiddleware
from .config import settings
from .database import init_db
from .routers import health, products, sessions, rpa
from .services import rpa_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
#  RPA ランナー（Phase 2 で rpa/ モジュールに実装）
# ──────────────────────────────────────────────────────────

async def _rpa_runner(job_id: str) -> None:
    """
    RPA ジョブを実行するスタブ。
    Phase 2 で rpa/runner.py に実装し、ここからインポートする。
    """
    from .database import update_rpa_job, get_session_items, get_rpa_job
    job = get_rpa_job(job_id)
    if not job:
        return

    logger.info(f"[RPA] ジョブ開始: {job_id} / session={job['session_id']}")
    update_rpa_job(job_id, status="running", step="開始")

    try:
        # Phase 2 実装後にここを置き換える
        # from rpa.runner import run_slip_registration
        # await asyncio.to_thread(run_slip_registration, job_id)

        # ── スタブ: 現時点では3秒待って完了扱いにする ──
        await asyncio.sleep(3)
        update_rpa_job(job_id, status="done", step="完了", sent_flag=1)
        logger.info(f"[RPA] ジョブ完了: {job_id}")

    except Exception as e:
        update_rpa_job(job_id, status="failed", step="エラー", error=str(e))
        logger.error(f"[RPA] ジョブ失敗: {job_id} / {e}")
        raise


# ──────────────────────────────────────────────────────────
#  ライフサイクル
# ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    init_db()
    logger.info("DB 初期化完了")
    logger.info(f"PIN認証: {'有効' if settings.get('pin') else '無効（未設定）'}")
    logger.info(f"楽天API: {'設定済み' if settings.get('rakuten_app_id') else '未設定'}")

    # RPA バックグラウンドワーカーを起動
    worker_task = asyncio.create_task(rpa_queue.worker(_rpa_runner))
    logger.info("RPA ワーカー起動")

    yield  # サーバー稼働中

    # 終了時
    worker_task.cancel()
    logger.info("サーバー終了")


# ──────────────────────────────────────────────────────────
#  アプリケーション
# ──────────────────────────────────────────────────────────

app = FastAPI(
    title="JANスキャナー 仕入管理サーバー",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS（同一LAN内のFlutterアプリからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# PIN認証ミドルウェア
app.add_middleware(PinAuthMiddleware)

# ルーター登録
app.include_router(health.router)
app.include_router(products.router)
app.include_router(sessions.router)
app.include_router(rpa.router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "JANスキャナー 仕入管理サーバー 稼働中"}


if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.get("host", "0.0.0.0"),
        port=int(settings.get("port", 8765)),
        reload=False,
    )
