import os
import subprocess
import sys
from pathlib import Path


def execute_generated_script(target_file: str = "output_script.py") -> tuple[bool, str]:
    path = Path(target_file)
    if not path.exists():
        return (
            False,
            f"❌ エラー: '{target_file}' が見つかりません。\n先にギターを弾いてプログラムを生成してください！",
        )

    code_content = path.read_text(encoding="utf-8")
    if not code_content.strip():
        return False, "(ファイルは空です。コードが生成されていません)"

    run_env = os.environ.copy()
    run_env["PYTHONUTF8"] = "1"
    run_env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, target_file],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=run_env,
        check=False,
    )

    if result.returncode == 0:
        stdout = result.stdout.strip()
        message = "✅ 実行結果:\n" + (stdout if stdout else "(標準出力なし)")
        return True, message

    stderr = result.stderr.strip()
    if not stderr:
        stderr = result.stdout.strip()
    message = "❌ 実行時にエラーが発生しました:\n" + (
        stderr if stderr else "(エラー出力なし)"
    )
    return False, message


def run_generated_script(target_file="output_script.py"):
    path = Path(target_file)

    if not path.exists():
        print(f"❌ エラー: '{target_file}' が見つかりません。")
        print("先にギターを弾いてプログラムを生成してください！")
        return

    print("=" * 50)
    print(f" 🎸 実行するプログラム: {target_file}")
    print("=" * 50)

    with open(path, "r", encoding="utf-8") as f:
        code_content = f.read()

    if not code_content.strip():
        print(" (ファイルは空です。コードが生成されていません)")
        return

    print(code_content)
    print("=" * 50)
    print("🚀 実行を開始します...\n")

    ok, message = execute_generated_script(target_file)
    print("-" * 30)
    print(message)
    print("-" * 30)
    if ok:
        print("✨ プログラムは正常に終了しました！")


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    run_generated_script()
