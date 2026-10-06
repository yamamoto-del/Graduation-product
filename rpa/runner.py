"""
rpa/runner.py
弥生販売 26 へのUI自動操作。pywinauto を使用。

処理内容:
  1. 弥生販売 26 が起動しているか確認（バージョンチェック）
  2. 仕入伝票の新規登録
  3. 不明商品がある場合は商品マスタに新規登録
  4. 完了後にCSVエクスポートしてマスタを再同期
"""

import logging
import sys
import time
from pathlib import Path

# server パッケージへのパスを通す
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.database import (
    get_rpa_job, get_session_items, update_rpa_job,
    upsert_product,
)
from server.services.master_sync import import_csv

logger = logging.getLogger(__name__)

# ─── 弥生販売 26 の設定 ─────────────────────────────────────
YAYOI_WINDOW_TITLE = "弥生 販売 26"
YAYOI_APP_CLASS    = "Td2MainForm"  # 弥生販売のメインフォームクラス名
CSV_EXPORT_PATH    = Path.home() / "Documents" / "yayoi_export" / "products.csv"


def run_slip_registration(job_id: str) -> None:
    """
    仕入伝票登録のメインエントリ。
    server/main.py の _rpa_runner から asyncio.to_thread で呼び出す。
    """
    try:
        import pywinauto
        from pywinauto.application import Application
        from pywinauto import timings
        timings.Timings.slow()
    except ImportError:
        raise RuntimeError(
            "pywinauto がインストールされていません。\n"
            "pip install pywinauto を実行してください。"
        )

    job = get_rpa_job(job_id)
    if not job:
        raise ValueError(f"ジョブが見つかりません: {job_id}")

    session_id = job["session_id"]
    items = get_session_items(session_id)

    # ── Step 1: 弥生販売 26 の起動確認 ───────────────────────
    _update(job_id, "弥生販売起動確認中")
    app = _connect_yayoi()

    # ── Step 2: 不明商品を先にマスタ登録 ──────────────────────
    unknown_items = [i for i in items if i["is_unknown"]]
    for idx, item in enumerate(unknown_items, 1):
        _update(job_id, f"商品マスタ登録 ({idx}/{len(unknown_items)}): {item['product_name']}")
        _register_product_master(app, item)
        # SQLite マスタにも登録
        upsert_product(
            jan_code=item["jan_code"],
            product_name=item["product_name"],
            unit_price=item["unit_price"],
            supplier=item["supplier"],
            unit=item["unit"],
        )

    # ── Step 3: 仕入伝票を新規登録 ────────────────────────────
    _update(job_id, "仕入伝票 新規入力画面を開いています")
    _open_slip_entry(app)

    for idx, item in enumerate(items, 1):
        _update(job_id, f"明細入力 ({idx}/{len(items)}): {item['product_name']}")
        _input_slip_line(app, item, is_first=(idx == 1))

    # ── Step 4: 登録確定 ──────────────────────────────────────
    _update(job_id, "伝票を登録しています")
    _confirm_slip(app)
    update_rpa_job(job_id, status="running", step="伝票登録完了", sent_flag=1)

    # ── Step 5: CSVエクスポート → SQLite 再同期 ───────────────
    _update(job_id, "商品マスタをCSVエクスポート中")
    _export_master_csv(app)
    if CSV_EXPORT_PATH.exists():
        _update(job_id, "SQLiteマスタを再同期中")
        import_csv(CSV_EXPORT_PATH, encoding="shift_jis")

    update_rpa_job(job_id, status="done", step="完了", sent_flag=1)
    logger.info(f"[RPA] ジョブ完了: {job_id}")


# ──────────────────────────────────────────────────────────
#  内部ヘルパー
# ──────────────────────────────────────────────────────────

def _update(job_id: str, step: str) -> None:
    logger.info(f"[RPA] {step}")
    update_rpa_job(job_id, status="running", step=step)


def _connect_yayoi():
    """弥生販売 26 のメインウィンドウに接続する。"""
    from pywinauto.application import Application
    try:
        app = Application(backend="uia").connect(title_re=f".*{YAYOI_WINDOW_TITLE}.*")
        win = app.window(title_re=f".*{YAYOI_WINDOW_TITLE}.*")
        win.wait("ready", timeout=10)
        return app
    except Exception:
        raise RuntimeError(
            f"弥生販売 26（ウィンドウタイトル: {YAYOI_WINDOW_TITLE}）に接続できません。\n"
            "弥生販売 26 を起動してから再実行してください。"
        )


def _open_slip_entry(app) -> None:
    """仕入伝票 → 新規入力画面を開く。"""
    win = app.window(title_re=f".*{YAYOI_WINDOW_TITLE}.*")
    win.set_focus()
    time.sleep(0.5)
    # メニュー: 取引(T) → 仕入伝票入力(N)
    win.menu_select("取引(&T)->仕入伝票入力(&N)")
    time.sleep(1.0)


def _input_slip_line(app, item, is_first: bool = False) -> None:
    """
    仕入伝票入力画面に明細行を入力する。
    弥生販売 26 の仕入伝票入力は、Tabキーでフィールドを移動する方式。
    """
    from pywinauto import keyboard
    entry_win = app.window(title_re=".*仕入伝票入力.*")
    entry_win.wait("ready", timeout=10)

    if is_first:
        # 最初の行: 仕入先コードや日付を入力（省略時は弥生デフォルト）
        pass

    # 商品コードフィールドに JANコードを入力
    jan_field = entry_win.child_window(auto_id="edtShouhinCode")
    jan_field.set_focus()
    jan_field.set_edit_text(item["jan_code"])
    keyboard.send_keys("{TAB}")
    time.sleep(0.3)

    # 数量フィールド
    qty_field = entry_win.child_window(auto_id="edtSuuryo")
    qty_field.set_edit_text(str(item["quantity"]))
    keyboard.send_keys("{TAB}")
    time.sleep(0.2)

    # 次の行へ
    keyboard.send_keys("{ENTER}")
    time.sleep(0.3)


def _confirm_slip(app) -> None:
    """仕入伝票を登録する。"""
    from pywinauto import keyboard
    entry_win = app.window(title_re=".*仕入伝票入力.*")
    # 登録ボタン（F12 または「登録」ボタン）
    try:
        btn = entry_win.child_window(title="登録", control_type="Button")
        btn.click()
    except Exception:
        keyboard.send_keys("{F12}")
    time.sleep(1.0)


def _register_product_master(app, item) -> None:
    """
    商品マスタに新規商品を登録する。
    メニュー: マスタ(M) → 商品マスタ(S)
    """
    from pywinauto import keyboard
    win = app.window(title_re=f".*{YAYOI_WINDOW_TITLE}.*")
    win.set_focus()
    win.menu_select("マスタ(&M)->商品マスタ(&S)")
    time.sleep(1.0)

    master_win = app.window(title_re=".*商品マスタ.*")
    master_win.wait("ready", timeout=10)

    # 新規ボタン
    try:
        btn_new = master_win.child_window(title="新規", control_type="Button")
        btn_new.click()
    except Exception:
        keyboard.send_keys("%N")  # Alt+N
    time.sleep(0.5)

    detail_win = app.window(title_re=".*商品マスタ.*")
    # 商品コード（JANコードを使用）
    detail_win.child_window(auto_id="edtShouhinCode").set_edit_text(item["jan_code"][:16])
    keyboard.send_keys("{TAB}")
    # 商品名
    detail_win.child_window(auto_id="edtShouhinName").set_edit_text(item["product_name"][:40])
    keyboard.send_keys("{TAB}")
    # 単位
    detail_win.child_window(auto_id="edtTani").set_edit_text(item["unit"])
    keyboard.send_keys("{TAB}")
    # 仕入単価
    detail_win.child_window(auto_id="edtShiireKakaku").set_edit_text(str(int(item["unit_price"])))
    keyboard.send_keys("{TAB}")

    time.sleep(0.3)
    # 登録ボタン
    try:
        btn_save = detail_win.child_window(title="登録", control_type="Button")
        btn_save.click()
    except Exception:
        keyboard.send_keys("{F12}")
    time.sleep(0.8)

    # 商品マスタウィンドウを閉じる
    try:
        master_win.close()
    except Exception:
        keyboard.send_keys("%{F4}")
    time.sleep(0.5)


def _export_master_csv(app) -> None:
    """
    商品マスタをCSVエクスポートする。
    メニュー: マスタ(M) → 商品マスタ(S) → ファイル → CSVエクスポート
    出力先: CSV_EXPORT_PATH
    """
    from pywinauto import keyboard
    win = app.window(title_re=f".*{YAYOI_WINDOW_TITLE}.*")
    win.set_focus()
    win.menu_select("マスタ(&M)->商品マスタ(&S)")
    time.sleep(1.0)

    master_win = app.window(title_re=".*商品マスタ.*")
    master_win.wait("ready", timeout=10)
    master_win.menu_select("ファイル(&F)->CSVエクスポート(&E)")
    time.sleep(0.8)

    # エクスポートダイアログ: ファイルパスを指定して保存
    export_dialog = app.window(title_re=".*エクスポート.*|.*名前を付けて保存.*")
    try:
        export_dialog.wait("ready", timeout=8)
        CSV_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        filename_field = export_dialog.child_window(auto_id="1148")  # ファイル名フィールド
        filename_field.set_edit_text(str(CSV_EXPORT_PATH))
        keyboard.send_keys("{ENTER}")
        time.sleep(1.5)
    except Exception as e:
        logger.warning(f"[RPA] CSVエクスポートダイアログの操作に失敗: {e}")

    try:
        master_win.close()
    except Exception:
        pass
