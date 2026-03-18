import os
import time
import json
from pathlib import Path

class GuitarCodeGenerator:
    def __init__(self, mapping_file_path: str = "code_mapping.json"):
        """
        初期化時にJSONファイルから対応表を読み込む
        """
        self.code_mapping = {}
        self._load_mapping(mapping_file_path)
        
        # 生成されたコードの各行を保持するリスト
        self.generated_lines = []

    def _load_mapping(self, filepath: str):
        """JSONファイルから対応表を読み込んで辞書に格納する"""
        path = Path(filepath)
        if not path.exists():
            print(f"⚠️ 警告: マッピングファイル '{filepath}' が見つかりません。")
            print("  デフォルトの空の辞書で開始します。")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.code_mapping = json.load(f)
            print(f"✅ 対応表 '{filepath}' を読み込みました。({len(self.code_mapping)}件)")
        except json.JSONDecodeError:
            print(f"❌ エラー: '{filepath}' のJSONの形式が不正です。")
            
    def receive_chord(self, chord_name: str):
        """
        第2のスクリプトからコード名を受け取り、画面を更新する
        """
        # 辞書に登録されていないコード（誤検知や未定義）は無視する
        if chord_name not in self.code_mapping:
            return

        # 対応するPython構文を取得してリストに追加
        snippet = self.code_mapping[chord_name]
        self.generated_lines.append(snippet)

        # ターミナルの表示を更新（ライブコーディング演出）
        self._render_terminal()

    def _render_terminal(self):
        """
        ターミナルをクリアして、現在のスクリプトの状態をエディタ風に表示する
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 45)
        print(" 🎸 LIVE GUITAR CODER 🎸 (終了は Ctrl+C)")
        print("=" * 45)
        
        for i, line in enumerate(self.generated_lines):
            print(f"{i + 1:3d} | {line}")
            
        print("-" * 45)
        print("(Listening for next chord...)")

    def get_final_script(self) -> str:
        """
        リストに溜まった文字列を結合し、最終的なスクリプト文字列(str)として出力する
        """
        return "\n".join(self.generated_lines)


# ==========================================
# 🧪 単体テスト用シミュレーション
# ==========================================
if __name__ == "__main__":
    # JSONファイル名を指定してインスタンス化
    generator = GuitarCodeGenerator("code_mapping.json")
    
    mock_incoming_chords = [
        "C Major", 
        "Unknown Noise", 
        "G Power", 
        "D Single", 
        "D Single", 
        "C Single"
    ]
    
    # 演出のため少し待つ
    time.sleep(1)
    
    try:
        for chord in mock_incoming_chords:
            time.sleep(1) 
            generator.receive_chord(chord)
            
        time.sleep(1)
        
    except KeyboardInterrupt:
        pass
        
    final_script_str = generator.get_final_script()
    
    os.system('cls' if os.name == 'nt' else 'clear')
    print("✅ 最終出力文字列 (str) の中身:\n")
    print(repr(final_script_str))