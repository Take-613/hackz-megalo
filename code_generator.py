import os
import json
from pathlib import Path

class GuitarCodeGenerator:
    def __init__(self, mapping_file_path: str = "code_mapping.json"):
        self.code_mapping = {}
        self._load_mapping(mapping_file_path)
        
        self.generated_lines = []
        self.current_line_str = ""
        
        self.current_node = self.code_mapping 
        self.current_message = "(Listening for next chord...)"

    def _load_mapping(self, filepath: str):
        path = Path(filepath)
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.code_mapping = json.load(f)
        except json.JSONDecodeError:
            pass
            
    def receive_chord(self, chord_name: str):
        if chord_name.startswith("_"): return

        if chord_name in self.current_node:
            next_step = self.current_node[chord_name]
            
            if isinstance(next_step, str):
                if next_step == "_CMD_NEWLINE":
                    self.generated_lines.append(self.current_line_str)
                    self.current_line_str = ""
                elif next_step == "_CMD_CLOSE":
                    self.current_line_str += ")"
                elif next_step == "_CMD_DELETE":
                    # --- 変更箇所：1行削除のロジックのみ ---
                    if len(self.current_line_str) > 0:
                        self.current_line_str = ""
                    elif len(self.generated_lines) > 0:
                        self.generated_lines.pop()
                    # ---------------------------------------
                else:
                    self.current_line_str += next_step
                
                self.current_node = self.code_mapping
                self.current_message = "(Listening for next chord...)"
                
            elif isinstance(next_step, dict):
                self.current_node = next_step
                self.current_message = self.current_node.get("_message", f"⏳ 続きを待機中...")
                
        elif chord_name in self.code_mapping:
            self.current_node = self.code_mapping[chord_name]
            if isinstance(self.current_node, str):
                self.current_line_str += self.current_node
                self.current_node = self.code_mapping
                self.current_message = "(Listening for next chord...)"
            else:
                self.current_message = self.current_node.get("_message", f"⏳ 新しく開始...")

        self._render_terminal()

    def _render_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 70)
        print(" 🎸 GUITAR TYPING KEYBOARD 🎸")
        print("=" * 70)
        
        for i, line in enumerate(self.generated_lines):
            for sub_line in line.split('\n'):
                print(f" {i + 1:3d} | {sub_line}")
                
        current_line_num = len(self.generated_lines) + 1
        print(f" {current_line_num:3d} > {self.current_line_str} ✍️")
            
        print("-" * 70)
        print(f" {self.current_message}")

    def get_final_script(self) -> str:
        final_lines = self.generated_lines.copy()
        if self.current_line_str:
            final_lines.append(self.current_line_str)
        return "\n".join(final_lines)