"""
server/routers/sessions.py
セッション管理 (作成 / 参照 / スキャン追加 / 削除 / 確定)
"""

from fastapi import APIRouter, HTTPException

from ..database import (
    create_session, get_session, touch_session, update_session_status,
    get_session_items, add_session_item, delete_session_item,
    get_product, upsert_product, create_rpa_job,
)
from ..models import (
    SessionCreateRequest, SessionResponse, ScanItemRequest,
    ScanItemResponse, MessageResponse,
)
from ..services import rpa_queue

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_response(row, items=None) -> SessionResponse:
    count = len(items) if items is not None else 0
    return SessionResponse(
        id=row["id"],
        created_by=row["created_by"],
        status=row["status"],
        created_at=row["created_at"],
        last_activity=row["last_activity"],
        item_count=count,
    )


def _require_session(session_id: str):
    row = get_session(session_id)
    if not row:
        raise HTTPException(404, "セッションが見つかりません。")
    if row["status"] not in ("active",):
        raise HTTPException(409, f"セッションは既に {row['status']} 状態です。")
    return row


# ── セッション作成 ────────────────────────────────────────

@router.post("", response_model=SessionResponse, status_code=201)
async def create_new_session(body: SessionCreateRequest):
    session_id = create_session(body.created_by)
    row = get_session(session_id)
    return _session_response(row)


# ── セッション参照 ────────────────────────────────────────

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_info(session_id: str):
    row = get_session(session_id)
    if not row:
        raise HTTPException(404, "セッションが見つかりません。")
    items = get_session_items(session_id)
    return _session_response(row, items)


# ── スキャンアイテム追加 ──────────────────────────────────

@router.post("/{session_id}/items", response_model=ScanItemResponse, status_code=201)
async def add_item(session_id: str, body: ScanItemRequest):
    row = _require_session(session_id)
    touch_session(session_id)

    # 商品マスタから検索
    product = get_product(body.jan_code)

    # 不明商品 or 手入力で上書き
    is_unknown = product is None
    product_name = body.product_name or (product["product_name"] if product else "")
    unit_price   = body.unit_price   if body.unit_price is not None else (product["unit_price"] if product else 0.0)
    supplier     = body.supplier     if body.supplier is not None   else (product["supplier"]   if product else "")
    unit         = body.unit         if body.unit is not None       else (product["unit"]        if product else "個")

    if not product_name:
        raise HTTPException(422, "商品名が不明です。手入力で商品名を指定してください。")

    item_id = add_session_item(
        session_id=session_id,
        jan_code=body.jan_code,
        product_name=product_name,
        unit_price=unit_price,
        supplier=supplier,
        unit=unit,
        quantity=body.quantity,
        is_unknown=is_unknown,
    )

    return ScanItemResponse(
        id=item_id,
        session_id=session_id,
        jan_code=body.jan_code,
        product_name=product_name,
        unit_price=unit_price,
        supplier=supplier,
        unit=unit,
        quantity=body.quantity,
        is_unknown=is_unknown,
        scanned_at="",
    )


# ── スキャンアイテム一覧 ──────────────────────────────────

@router.get("/{session_id}/items", response_model=list[ScanItemResponse])
async def list_items(session_id: str):
    row = get_session(session_id)
    if not row:
        raise HTTPException(404, "セッションが見つかりません。")
    items = get_session_items(session_id)
    return [
        ScanItemResponse(
            id=i["id"], session_id=session_id,
            jan_code=i["jan_code"], product_name=i["product_name"],
            unit_price=i["unit_price"], supplier=i["supplier"],
            unit=i["unit"], quantity=i["quantity"],
            is_unknown=bool(i["is_unknown"]), scanned_at=i["scanned_at"],
        )
        for i in items
    ]


# ── スキャンアイテム削除 ──────────────────────────────────

@router.delete("/{session_id}/items/{item_id}", response_model=MessageResponse)
async def remove_item(session_id: str, item_id: int):
    _require_session(session_id)
    touch_session(session_id)
    delete_session_item(item_id)
    return MessageResponse(message="削除しました。")


# ── 伝票確定（RPAキューへ積む）──────────────────────────

@router.post("/{session_id}/confirm", response_model=dict)
async def confirm_session(session_id: str):
    row = _require_session(session_id)
    items = get_session_items(session_id)
    if not items:
        raise HTTPException(422, "スキャンアイテムが1件もありません。")

    # 不明商品に未入力がないか確認
    for item in items:
        if not item["product_name"]:
            raise HTTPException(
                422, f"JANコード {item['jan_code']} の商品名が入力されていません。"
            )

    update_session_status(session_id, "confirmed")

    # RPAジョブ作成 → キューへ
    job_id = create_rpa_job(session_id)
    await rpa_queue.enqueue(job_id)
    queue_len = rpa_queue.get_queue_length()

    return {
        "message": "伝票を確定しました。RPAが順番に処理します。",
        "job_id": job_id,
        "queue_position": queue_len,
    }
