"""
server/services/rpa_queue.py
asyncio.Queue を使った RPA 排他制御キュー。
1件ずつ順番にRPAジョブを処理することで弥生販売の同時操作を防ぐ。
"""

import asyncio
import logging
from datetime import datetime

from ..database import (
    get_session_items, update_rpa_job, update_session_status,
    get_rpa_job, get_pending_rpa_jobs,
)

logger = logging.getLogger(__name__)

# グローバルキュー（job_id を積む）
_queue: asyncio.Queue[str] = asyncio.Queue()
_current_job_id: str | None = None


def get_queue_length() -> int:
    return _queue.qsize()


def get_current_job_id() -> str | None:
    return _current_job_id


async def enqueue(job_id: str) -> None:
    """RPAジョブをキューに積む。"""
    await _queue.put(job_id)
    logger.info(f"[RPA] ジョブをキューに追加: {job_id}（待機中: {_queue.qsize()} 件）")


async def worker(rpa_runner) -> None:
    """
    バックグラウンドワーカー。キューからジョブを取り出して順番に実行する。
    rpa_runner: async callable(job_id: str) -> None
    """
    global _current_job_id
    logger.info("[RPA] ワーカー起動")

    while True:
        job_id = await _queue.get()
        _current_job_id = job_id
        logger.info(f"[RPA] ジョブ実行開始: {job_id}")

        try:
            await rpa_runner(job_id)
        except Exception as e:
            logger.error(f"[RPA] ジョブ失敗: {job_id} / {e}")
            update_rpa_job(job_id, status="failed", step="エラー", error=str(e))
        finally:
            _current_job_id = None
            _queue.task_done()
