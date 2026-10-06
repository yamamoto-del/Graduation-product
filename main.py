"""
main.py  ─  JAN コード読み取り・自動入力ツール
========================================================
【機能】
  1. カメラ映像をリアルタイムでスキャンし JAN コードを検出
  2. 検出したコードを現在フォーカス中のウィンドウへ自動入力
  3. スキャン履歴を Excel に自動記録
  4. 画像ファイルからの読み取りにも対応

【依存ライブラリのインストール】
  pip install -r requirements.txt

【使い方】
  python main.py
========================================================
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import cv2
from PIL import Image, ImageTk

# モジュールのパスを通す
sys.path.insert(0, os.path.dirname(__file__))
from modules.scanner import decode_from_frame, decode_from_image_file, is_jan_code
from modules.excel_writer import append_scan
from modules.auto_input import type_code

# ── 設定読み込み ────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, encoding="utf-8") as f:
    CFG = json.load(f)


# ══════════════════════════════════════════════════════════
#  メインアプリケーションクラス
# ══════════════════════════════════════════════════════════
class JanScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📦 JAN コード読み取り・自動入力ツール")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        # 状態変数
        self._cap: cv2.VideoCapture | None = None
        self._running = False
        self._auto_input_on = tk.BooleanVar(value=False)
        self._excel_log_on = tk.BooleanVar(value=True)
        self._last_code = ""
        self._last_scan_time = 0.0
        self._scan_count = 0
        self._history: list[dict] = []

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI 構築 ─────────────────────────────────────────────
    def _build_ui(self):
        # ── ヘッダー
        header = tk.Frame(self, bg="#313244", pady=8)
        header.pack(fill="x")
        tk.Label(
            header, text="📦 JAN コード読み取り・自動入力ツール",
            font=("Yu Gothic UI", 14, "bold"),
            bg="#313244", fg="#cdd6f4"
        ).pack()

        # ── メインコンテンツ（左：カメラ、右：コントロール）
        content = tk.Frame(self, bg="#1e1e2e")
        content.pack(fill="both", expand=True, padx=10, pady=8)

        # ─ 左：カメラプレビュー
        left = tk.Frame(content, bg="#1e1e2e")
        left.pack(side="left", fill="both", expand=True)

        self._canvas = tk.Canvas(left, width=480, height=360, bg="#11111b", highlightthickness=2, highlightbackground="#585b70")
        self._canvas.pack()
        self._canvas.create_text(240, 180, text="カメラ停止中", fill="#585b70", font=("Yu Gothic UI", 12))

        # ─ 右：コントロールパネル
        right = tk.Frame(content, bg="#1e1e2e", width=280)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        # カメラ操作
        cam_frame = self._make_card(right, "🎥 カメラ操作")
        tk.Button(
            cam_frame, text="▶ カメラ開始", command=self._start_camera,
            **self._btn_style("#a6e3a1")
        ).pack(fill="x", pady=3)
        tk.Button(
            cam_frame, text="⏹ カメラ停止", command=self._stop_camera,
            **self._btn_style("#f38ba8")
        ).pack(fill="x", pady=3)
        tk.Button(
            cam_frame, text="🖼 画像ファイルから読み取り", command=self._scan_from_image,
            **self._btn_style("#89b4fa")
        ).pack(fill="x", pady=3)

        # オプション
        opt_frame = self._make_card(right, "⚙️ オプション")
        tk.Checkbutton(
            opt_frame, text="🖱 フォーカス中のウィンドウへ自動入力",
            variable=self._auto_input_on,
            bg="#313244", fg="#cdd6f4", selectcolor="#45475a",
            activebackground="#313244", activeforeground="#cdd6f4",
            font=("Yu Gothic UI", 9)
        ).pack(anchor="w")
        tk.Checkbutton(
            opt_frame, text="📊 Excel にスキャン履歴を記録",
            variable=self._excel_log_on,
            bg="#313244", fg="#cdd6f4", selectcolor="#45475a",
            activebackground="#313244", activeforeground="#cdd6f4",
            font=("Yu Gothic UI", 9)
        ).pack(anchor="w")

        # ── 最後に読み取ったコード表示
        result_frame = self._make_card(right, "📋 最後に読み取ったコード")
        self._result_var = tk.StringVar(value="（まだスキャンしていません）")
        tk.Label(
            result_frame, textvariable=self._result_var,
            bg="#313244", fg="#f9e2af",
            font=("Consolas", 13, "bold"), wraplength=240
        ).pack(pady=4)
        self._count_var = tk.StringVar(value="スキャン数: 0")
        tk.Label(
            result_frame, textvariable=self._count_var,
            bg="#313244", fg="#a6e3a1", font=("Yu Gothic UI", 9)
        ).pack()

        # ── 履歴テーブル
        hist_frame = self._make_card(self, "📜 スキャン履歴", padx=10)
        hist_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cols = ("no", "code", "type", "time")
        self._tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=8)
        self._tree.heading("no", text="No.")
        self._tree.heading("code", text="JANコード")
        self._tree.heading("type", text="種別")
        self._tree.heading("time", text="スキャン日時")
        self._tree.column("no", width=40, anchor="center")
        self._tree.column("code", width=160)
        self._tree.column("type", width=80, anchor="center")
        self._tree.column("time", width=180)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#313244", foreground="#cdd6f4",
                         fieldbackground="#313244", rowheight=22)
        style.configure("Treeview.Heading", background="#45475a", foreground="#cdd6f4")
        style.map("Treeview", background=[("selected", "#585b70")])

        scrollbar = ttk.Scrollbar(hist_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── ステータスバー
        self._status_var = tk.StringVar(value="準備完了")
        tk.Label(
            self, textvariable=self._status_var,
            bg="#181825", fg="#6c7086",
            font=("Yu Gothic UI", 8), anchor="w", padx=8
        ).pack(fill="x", side="bottom")

    def _make_card(self, parent, title: str, padx=0):
        outer = tk.Frame(parent, bg="#1e1e2e")
        outer.pack(fill="x", pady=4, padx=padx)
        tk.Label(outer, text=title, bg="#1e1e2e", fg="#6c7086",
                 font=("Yu Gothic UI", 8)).pack(anchor="w")
        card = tk.Frame(outer, bg="#313244", padx=8, pady=6)
        card.pack(fill="x")
        return card

    def _btn_style(self, fg):
        return dict(
            bg="#45475a", fg=fg, activebackground="#585b70", activeforeground=fg,
            font=("Yu Gothic UI", 9, "bold"), relief="flat", cursor="hand2", pady=4
        )

    # ── カメラ操作 ───────────────────────────────────────────
    def _start_camera(self):
        if self._running:
            return
        idx = CFG.get("camera_index", 0)
        self._cap = cv2.VideoCapture(idx)
        if not self._cap.isOpened():
            messagebox.showerror("エラー", f"カメラ（インデックス {idx}）が開けません。\n"
                                 "config.json の camera_index を変更してください。")
            return
        self._running = True
        self._set_status("カメラ起動中...")
        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _stop_camera(self):
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None
        self._canvas.delete("all")
        self._canvas.create_text(240, 180, text="カメラ停止中", fill="#585b70",
                                  font=("Yu Gothic UI", 12))
        self._set_status("カメラ停止")

    def _camera_loop(self):
        interval = CFG.get("scan_interval_ms", 200) / 1000.0
        self._set_status("スキャン中...")
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret:
                break
            # バーコード検出
            results = decode_from_frame(frame)
            for r in results:
                self._draw_rect(frame, r["rect"], r["code"])
                self._on_code_detected(r["code"], r["type"])
            # プレビュー更新（メインスレッドへ）
            self.after(0, self._update_preview, frame)
            time.sleep(interval)
        self._running = False

    def _draw_rect(self, frame, rect, label: str):
        x, y, w, h = rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 100), 2)
        cv2.putText(frame, label, (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2)

    def _update_preview(self, frame):
        """OpenCV フレーム → tkinter Canvas へ描画。"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img.thumbnail((480, 360))
        self._tk_img = ImageTk.PhotoImage(img)
        self._canvas.config(width=img.width, height=img.height)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

    # ── 画像ファイル読み取り ────────────────────────────────
    def _scan_from_image(self):
        path = filedialog.askopenfilename(
            title="画像ファイルを選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.gif"), ("すべて", "*.*")]
        )
        if not path:
            return
        try:
            results = decode_from_image_file(path)
            if not results:
                messagebox.showinfo("結果", "バーコードが検出されませんでした。")
                return
            for r in results:
                self._on_code_detected(r["code"], r["type"])
            messagebox.showinfo("結果", f"{len(results)} 件のバーコードを検出しました。")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    # ── コード検出時の処理 ────────────────────────────────
    def _on_code_detected(self, code: str, code_type: str):
        now = time.time()
        cooldown = CFG.get("duplicate_cooldown_sec", 3)
        # 同じコードを短時間に連続検出しない
        if code == self._last_code and (now - self._last_scan_time) < cooldown:
            return
        self._last_code = code
        self._last_scan_time = now
        self._scan_count += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # UI 更新（メインスレッドへ）
        self.after(0, self._update_result_ui, code, code_type, ts)

        # 自動入力
        if self._auto_input_on.get():
            delay = CFG.get("auto_input_delay_sec", 0.05)
            suffix = CFG.get("auto_input_suffix", "enter")
            threading.Thread(
                target=type_code, args=(code, delay, suffix), daemon=True
            ).start()

        # Excel 記録
        if self._excel_log_on.get():
            excel_path = os.path.join(
                os.path.dirname(__file__),
                CFG.get("excel_output_path", "output/scan_log.xlsx")
            )
            sheet = CFG.get("sheet_name", "スキャン履歴")
            threading.Thread(
                target=append_scan, args=(excel_path, sheet, code, code_type), daemon=True
            ).start()

    def _update_result_ui(self, code: str, code_type: str, ts: str):
        jan_mark = "✅ JAN" if is_jan_code(code) else "⚠ 非JAN"
        self._result_var.set(code)
        self._count_var.set(f"スキャン数: {self._scan_count}　({jan_mark})")
        self._set_status(f"検出: {code}  ({code_type})  {ts}")
        # 履歴テーブルへ追加（先頭に挿入）
        self._tree.insert("", 0, values=(self._scan_count, code, code_type, ts))

    # ── ユーティリティ ────────────────────────────────────
    def _set_status(self, msg: str):
        self._status_var.set(msg)

    def _on_close(self):
        self._stop_camera()
        self.destroy()


# ── エントリポイント ────────────────────────────────────────
if __name__ == "__main__":
    app = JanScannerApp()
    app.mainloop()
