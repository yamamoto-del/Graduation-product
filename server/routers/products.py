"""
server/routers/products.py
GET /products/{jan_code}  —  JANコード照合。
POST /products/sync       —  弥生販売CSVを手動でインポート。
"""

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..database import get_product
from ..models import ProductResponse
from ..services.jan_lookup import lookup_jan
from ..services.master_sync import import_csv_bytes

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{jan_code}", response_model=ProductResponse)
async def get_product_by_jan(jan_code: str):
    """
    1. SQLite マスタDBを照合
    2. 見つからなければ 楽天API → Open Food Facts にフォールバック
    3. それでも見つからなければ is_unknown=True で空の商品情報を返す
    """
    row = get_product(jan_code)
    if row:
        return ProductResponse(
            jan_code=row["jan_code"],
            product_code=row["product_code"],
            product_name=row["product_name"],
            unit_price=row["unit_price"],
            supplier=row["supplier"],
            unit=row["unit"],
            is_unknown=False,
        )

    # 外部APIで検索
    result = await lookup_jan(jan_code)
    if result:
        return ProductResponse(
            jan_code=jan_code,
            product_code="",
            product_name=result["product_name"],
            unit_price=0.0,
            supplier="",
            unit="個",
            is_unknown=True,
        )

    # 完全不明
    return ProductResponse(
        jan_code=jan_code,
        product_code="",
        product_name="",
        unit_price=0.0,
        supplier="",
        unit="個",
        is_unknown=True,
    )


@router.post("/sync", tags=["products"])
async def sync_master_csv(file: UploadFile = File(...)):
    """
    弥生販売からエクスポートした商品マスタCSVをアップロードして同期する。
    文字コード: Shift_JIS（弥生販売の標準出力）
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "CSVファイルをアップロードしてください。")

    data = await file.read()
    try:
        count = import_csv_bytes(data, encoding="shift_jis")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"インポート中にエラーが発生しました: {e}")

    return {"message": f"{count} 件の商品マスタを同期しました。"}
