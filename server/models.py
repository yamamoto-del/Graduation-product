"""
server/models.py
FastAPI リクエスト / レスポンス用 Pydantic モデル。
"""

from pydantic import BaseModel, Field
from typing import Optional


# ──────────────────────────────────────────────────────────
#  商品マスタ
# ──────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    jan_code: str
    product_code: str
    product_name: str
    unit_price: float
    supplier: str
    unit: str
    is_unknown: bool = False          # 外部APIで補完した場合は True


class ProductManualInput(BaseModel):
    """不明JANコード時にスタッフが手入力する情報。"""
    product_name: str = Field(..., min_length=1)
    unit_price: float = Field(ge=0)
    supplier: str = ""
    unit: str = "個"


# ──────────────────────────────────────────────────────────
#  セッション
# ──────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    created_by: str = ""


class SessionResponse(BaseModel):
    id: str
    created_by: str
    status: str
    created_at: str
    last_activity: str
    item_count: int = 0


# ──────────────────────────────────────────────────────────
#  スキャンアイテム
# ──────────────────────────────────────────────────────────

class ScanItemRequest(BaseModel):
    jan_code: str = Field(..., min_length=8)
    quantity: int = Field(ge=1)
    # 不明商品の場合はこれらを手入力
    product_name: Optional[str] = None
    unit_price: Optional[float] = None
    supplier: Optional[str] = None
    unit: Optional[str] = None


class ScanItemResponse(BaseModel):
    id: int
    session_id: str
    jan_code: str
    product_name: str
    unit_price: float
    supplier: str
    unit: str
    quantity: int
    is_unknown: bool
    scanned_at: str


# ──────────────────────────────────────────────────────────
#  RPAジョブ
# ──────────────────────────────────────────────────────────

class RPAJobResponse(BaseModel):
    id: str
    session_id: str
    status: str          # queued | running | done | failed
    step: str
    error: str
    sent_flag: bool
    created_at: str
    updated_at: str


class QueueStatusResponse(BaseModel):
    queue_length: int
    current_job: Optional[RPAJobResponse]
    recent_jobs: list[RPAJobResponse]


# ──────────────────────────────────────────────────────────
#  ヘルスチェック
# ──────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str                    # ok | degraded | error
    server: str = "ok"
    yayoi_running: bool
    yayoi_version: str
    db_ok: bool


# ──────────────────────────────────────────────────────────
#  共通レスポンス
# ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
