"""
auto_input.py
スキャンしたコードを現在フォーカスされているウィンドウに自動入力するモジュール
"""

import time
import pyautogui

# 誤操作防止のため最大入力速度を制限
pyautogui.PAUSE = 0.02
pyautogui.FAILSAFE = True  # 画面左上にマウスを移動すると緊急停止


def type_code(code: str, delay_sec: float = 0.05, suffix: str = "enter"):
    """
    現在フォーカスされているウィンドウにコードを入力する。

    Args:
        code: 入力する文字列
        delay_sec: 入力前の待機秒数（フォーカス移動のバッファ）
        suffix: 入力後のキー操作 ("enter" / "tab" / "none")
    """
    time.sleep(delay_sec)
    pyautogui.typewrite(code, interval=0.02)
    if suffix == "enter":
        pyautogui.press("enter")
    elif suffix == "tab":
        pyautogui.press("tab")
    # "none" の場合は何もしない
