"""
server/config.py
設定管理。環境変数 or config.server.json から読み込む。
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

_CONFIG_FILE = BASE_DIR / "config.server.json"

_DEFAULTS = {
    "pin": "0000",
    "host": "0.0.0.0",
    "port": 8765,
    "db_path": str(BASE_DIR / "data" / "master.db"),
    "log_path": str(BASE_DIR / "data" / "rpa_jobs.log"),
    "yayoi_exe_name": "販売26",          # 弥生販売 26 のプロセス名（部分一致）
    "yayoi_window_title": "弥生 販売 26", # ウィンドウタイトル（部分一致）
    "session_timeout_sec": 1800,          # 30分
    "rakuten_app_id": "",                 # 楽天ウェブサービス Application ID
}


def load() -> dict:
    """設定を辞書として返す。ファイルがなければデフォルト値を返す。"""
    cfg = dict(_DEFAULTS)
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def save(cfg: dict) -> None:
    """設定をファイルに保存する。"""
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# モジュール読み込み時に設定をロード
settings = load()
