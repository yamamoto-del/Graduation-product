"""
scanner.py
カメラまたは画像ファイルから JAN コード（EAN-13）を読み取るモジュール
"""

import cv2
from pyzbar import pyzbar
from typing import Optional


def decode_from_frame(frame) -> list[dict]:
    """
    OpenCV フレームから全バーコードをデコードして返す。

    Returns:
        list of dict: [{"code": str, "type": str, "rect": tuple}, ...]
    """
    results = []
    decoded = pyzbar.decode(frame)
    for barcode in decoded:
        data = barcode.data.decode("utf-8")
        btype = barcode.type  # EAN13, CODE128, etc.
        rect = barcode.rect   # (left, top, width, height)
        results.append({"code": data, "type": btype, "rect": rect})
    return results


def decode_from_image_file(path: str) -> list[dict]:
    """
    画像ファイルパスからバーコードを読み取る。
    """
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"画像が読み込めません: {path}")
    return decode_from_frame(img)


def is_jan_code(code: str) -> bool:
    """
    JAN コード（EAN-8 または EAN-13）かどうかを判定する。
    """
    return (len(code) in (8, 13)) and code.isdigit()
