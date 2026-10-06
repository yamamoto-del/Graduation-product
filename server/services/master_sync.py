"""
server/services/master_sync.py
弥生販売からエクスポートされた商品マスタCSVを
SQLite にインポートする。

弥生販売 26 の商品マスタCSVエクスポート手順:
  販売管理 > マスタ > 商品マスタ > ファイル > CSVエクスポート
  文字コード: Shift_JIS
  
期待されるCSVカラム（最低限）:
  商品コード, 商品名, 基準単価, 仕入先名, 単位, JANコード
"""

import csv
import io
from pathlib import Path

from ..database import bulk_upsert_products

# 弥生販売の標準エクスポートCSVのカラムマッピング
# キー: SQLiteカラム名, 値: CSVヘッダー候補リスト（いずれかにマッチすればOK）
_COLUMN_MAP = {
    "product_code": ["商品コード", "品番"],
    "product_name": ["商品名", "品名"],
    "unit_price":   ["基準単価", "仕入単価", "標準単価"],
    "supplier":     ["仕入先名", "仕入先"],
    "unit":         ["単位"],
    "jan_code":     ["JANコード", "JAN", "バーコード"],
}


def import_csv(csv_path: str | Path, encoding: str = "shift_jis") -> int:
    """
    弥生販売からエクスポートしたCSVを読み込み、SQLiteに一括インポートする。
    返り値: インポートした件数
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {path}")

    with open(path, encoding=encoding, newline="") as f:
        content = f.read()

    return _parse_and_import(content)


def import_csv_bytes(data: bytes, encoding: str = "shift_jis") -> int:
    """バイト列からCSVを読み込む（API経由アップロード用）。"""
    content = data.decode(encoding)
    return _parse_and_import(content)


def _parse_and_import(content: str) -> int:
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    # CSVヘッダーを正規化して内部カラム名にマッピング
    col_index: dict[str, str | None] = {}
    for internal_key, candidates in _COLUMN_MAP.items():
        col_index[internal_key] = _find_header(headers, candidates)

    if col_index["jan_code"] is None or col_index["product_name"] is None:
        raise ValueError(
            "CSVに JANコード または 商品名 のカラムが見つかりません。\n"
            f"検出されたヘッダー: {headers}"
        )

    rows = []
    for row in reader:
        jan = _get(row, col_index["jan_code"], "").strip()
        if not jan:
            continue  # JANコードなしはスキップ

        rows.append({
            "jan_code":     jan,
            "product_code": _get(row, col_index["product_code"], ""),
            "product_name": _get(row, col_index["product_name"], "不明"),
            "unit_price":   _to_float(_get(row, col_index["unit_price"], "0")),
            "supplier":     _get(row, col_index["supplier"], ""),
            "unit":         _get(row, col_index["unit"], "個"),
        })

    if not rows:
        return 0

    return bulk_upsert_products(rows)


def _find_header(headers: list[str], candidates: list[str]) -> str | None:
    for h in headers:
        if h.strip() in candidates:
            return h
    return None


def _get(row: dict, key: str | None, default: str) -> str:
    if key is None:
        return default
    return (row.get(key) or "").strip() or default


def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", "").replace("¥", "").strip())
    except (ValueError, AttributeError):
        return 0.0
