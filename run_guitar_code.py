import os
import sys
import subprocess
from pathlib import Path

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

    # 🌟 追加: 子プロセス（実行するPython）に強制的にUTF-8を使わせる魔法の環境変数
    run_env = os.environ.copy()
    run_env["PYTHONUTF8"] = "1"
    run_env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            [sys.executable, target_file],
            capture_output=True,
            text=True,
            encoding="utf-8", # 🌟 追加: 親プロセス側もUTF-8で読み取る
            env=run_env,      # 🌟 追加: 環境変数を渡す
            check=True
        )
        
        print("✅ 実行結果:")
        print("-" * 30)
        print(result.stdout)
        print("-" * 30)
        print("✨ プログラムは正常に終了しました！")
        
    except subprocess.CalledProcessError as e:
        print("❌ 実行時にエラーが発生しました:")
        print("-" * 30)
        print(e.stderr)
        print("-" * 30)

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    run_generated_script()