import os
import json
import re
from pathlib import Path

class GuitarCodeGenerator:
    def __init__(
        self,
        mapping_file_path: str = "code_mapping.json",
        render_terminal: bool = True,
    ):
        self.code_mapping = {}
        self._load_mapping(mapping_file_path)
        self.render_terminal = render_terminal
        
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

        if self.render_terminal:
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

    def get_next_action_state(self) -> tuple[str, list[tuple[str, str]]]:
        message = self.current_message
        if not isinstance(self.current_node, dict):
            return (message, [])

        choices: list[tuple[str, str]] = []
        for chord_name, next_step in self.current_node.items():
            if chord_name.startswith("_"):
                continue
            label = self._humanize_next_step(next_step)
            choices.append((chord_name, label))
        return (message, choices)

    def _humanize_next_step(self, next_step: object) -> str:
        if isinstance(next_step, dict):
            nested_message = str(next_step.get("_message", "")).strip()
            if nested_message:
                match = re.search(r"\[([^\]]+)\]", nested_message)
                if match:
                    return match.group(1)
                return nested_message
            return "詳細メニュー"

        if isinstance(next_step, str):
            command_labels = {
                "_CMD_NEWLINE": "確定/改行",
                "_CMD_CLOSE": "閉じる )",
                "_CMD_DELETE": "1行削除",
                "_CMD_EXIT": "終了",
            }
            if next_step in command_labels:
                return command_labels[next_step]

            text = next_step.strip()
            if not text:
                return "空入力"
            return text

        return "選択"