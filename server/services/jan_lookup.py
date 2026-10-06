"""
server/services/jan_lookup.py
外部JAN検索サービス。
1次: 楽天ウェブサービス商品検索API
2次: Open Food Facts API（食品補完）
"""

import httpx
from ..config import settings


async def lookup_jan(jan_code: str) -> dict | None:
    """
    JANコードから商品情報を取得する。
    見つかった場合は {"product_name": str, "source": str} を返す。
    見つからない場合は None を返す。
    """
    # 1次: 楽天API
    result = await _lookup_rakuten(jan_code)
    if result:
        return result

    # 2次: Open Food Facts
    result = await _lookup_openfoodfacts(jan_code)
    if result:
        return result

    return None


async def _lookup_rakuten(jan_code: str) -> dict | None:
    app_id = settings.get("rakuten_app_id", "")
    if not app_id:
        return None

    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    params = {
        "applicationId": app_id,
        "keyword": jan_code,
        "hits": 1,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("Items", [])
            if not items:
                return None
            item = items[0].get("Item", {})
            name = item.get("itemName", "").strip()
            if not name:
                return None
            return {"product_name": name, "source": "rakuten"}
    except Exception:
        return None


async def _lookup_openfoodfacts(jan_code: str) -> dict | None:
    url = f"https://world.openfoodfacts.org/api/v3/product/{jan_code}.json"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers={"User-Agent": "jan-scanner/1.0"})
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != "success":
                return None
            product = data.get("product", {})
            # 日本語名を優先して取得
            name = (
                product.get("product_name_ja")
                or product.get("product_name")
                or ""
            ).strip()
            if not name:
                return None
            return {"product_name": name, "source": "openfoodfacts"}
    except Exception:
        return None
