"""
setup.py  ─  ライブラリのインストールと動作確認スクリプト
実行方法: python setup.py
"""

import subprocess
import sys


def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


PACKAGES = [
    "opencv-python",
    "pyzbar",
    "openpyxl",
    "pyautogui",
    "Pillow",
]

if __name__ == "__main__":
    print("=" * 50)
    print("  JAN スキャナー ─ 依存ライブラリのインストール")
    print("=" * 50)
    for pkg in PACKAGES:
        print(f"\n[インストール中] {pkg} ...")
        try:
            install(pkg)
            print(f"  ✅ {pkg} インストール完了")
        except Exception as e:
            print(f"  ❌ {pkg} インストール失敗: {e}")

    print("\n" + "=" * 50)
    print("  動作確認中 ...")
    print("=" * 50)
    errors = []
    for mod in ["cv2", "pyzbar", "openpyxl", "pyautogui", "PIL"]:
        try:
            __import__(mod)
            print(f"  ✅ {mod} OK")
        except ImportError as e:
            print(f"  ❌ {mod} FAILED: {e}")
            errors.append(mod)

    if errors:
        print(f"\n⚠ 以下のモジュールに問題があります: {errors}")
    else:
        print("\n🎉 すべてのモジュールが正常にインポートできました！")
        print("   python main.py  でツールを起動してください。")
