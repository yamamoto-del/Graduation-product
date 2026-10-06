"""
server/routers/rpa.py
RPA キューの状態確認 / 手動再実行。
"""

from fastapi import APIRouter, HTTPException

from ..database import get_rpa_job, get_pending_rpa_jobs, update_rpa_job
from ..models import RPAJobResponse, QueueStatusResponse, MessageResponse
from ..services import rpa_queue

router = APIRouter(prefix="/rpa", tags=["rpa"])


def _to_response(row) -> RPAJobResponse:
    return RPAJobResponse(
        id=row["id"],
        session_id=row["session_id"] or "",
        status=row["status"],
        step=row["step"] or "",
        error=row["error"] or "",
        sent_flag=bool(row["sent_flag"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/queue", response_model=QueueStatusResponse, tags=["rpa"])
async def get_queue_status():
    """キューの状態・現在実行中のジョブ・直近の失敗ジョブを返す。"""
    current_id = rpa_queue.get_current_job_id()
    current = None
    if current_id:
        row = get_rpa_job(current_id)
        if row:
            current = _to_response(row)

    pending = get_pending_rpa_jobs()
    recent = [_to_response(r) for r in pending[:10]]

    return QueueStatusResponse(
        queue_length=rpa_queue.get_queue_length(),
        current_job=current,
        recent_jobs=recent,
    )


@router.post("/jobs/{job_id}/retry", response_model=MessageResponse, tags=["rpa"])
async def retry_job(job_id: str):
    """失敗したジョブを手動で再実行キューに積み直す。"""
    row = get_rpa_job(job_id)
    if not row:
        raise HTTPException(404, "ジョブが見つかりません。")
    if row["sent_flag"]:
        raise HTTPException(
            409, "このジョブはすでに弥生販売に送信済みです（二重登録防止）。"
        )
    if row["status"] not in ("failed",):
        raise HTTPException(409, f"再実行できる状態ではありません（現状: {row['status']}）。")

    update_rpa_job(job_id, status="queued", step="再キュー待ち", error="")
    await rpa_queue.enqueue(job_id)
    return MessageResponse(message=f"ジョブ {job_id} を再実行キューに追加しました。")
