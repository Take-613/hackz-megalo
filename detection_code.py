from __future__ import annotations

import argparse
import csv
from pathlib import Path

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# 辞書：ルート音からの半音の距離（インターバル）の組み合わせ
CHORD_DICTIONARY = {
    (0, 4, 7): "Major",  # ルート, 長3度, 完全5度
    (0, 3, 7): "Minor",  # ルート, 短3度, 完全5度
    (0, 7): "Power",  # ルート, 完全5度 (パワーコード)
    (0, 4, 7, 10): "7th",  # ルート, 長3度, 完全5度, 短7度
    (0, 4, 7, 11): "Major 7th",  # ルート, 長3度, 完全5度, 長7度
    (0, 3, 7, 10): "Minor 7th",  # ルート, 短3度, 完全5度, 短7度
    (0, 5, 7): "sus4",  # ルート, 完全4度, 完全5度
    (0, 2, 4, 7): "add9",  # ルート, 長2度(9th), 長3度, 完全5度
}


def analyze_chord(midi_notes: list[int]) -> str:
    """
    MIDIノート番号の配列を受け取り、コード名を判定する
    例: [48, 52, 55] -> "C Major"
    例: [60]         -> "C Single"
    """
    if not midi_notes:
        return "None"

    # 1. 重複する音（オクターブ違いの同じ音など）を排除し、低い順に並べる
    unique_notes = sorted(list(set(midi_notes)))

    # 2. 単音（1音だけ）の場合の処理
    if len(unique_notes) == 1:
        note_name = NOTE_NAMES[unique_notes[0] % 12]
        return f"{note_name} Single"

    # 3. 和音の場合、一番低い音を「ルート（基準）」とする
    lowest_note = unique_notes[0]
    root_pitch_class = lowest_note % 12
    root_name = NOTE_NAMES[root_pitch_class]

    # 4. ルート音からの相対的な距離（インターバル）を計算する
    intervals = set()
    for note in unique_notes:
        pitch_class = note % 12
        interval = (pitch_class - root_pitch_class) % 12
        intervals.add(interval)

    # 辞書のキーと合わせるためにソートしてタプル化
    intervals_tuple = tuple(sorted(list(intervals)))

    # 5. 辞書から検索する
    chord_type = CHORD_DICTIONARY.get(intervals_tuple)

    # 辞書に完全に一致しない組み合わせの場合は "Unknown" とする
    if chord_type is None:
        return f"{root_name} Unknown"

    return f"{root_name} {chord_type}"


def extract_pitch_midi_from_csv(csv_path: Path) -> list[int]:
    """
    basic-pitch の CSV から pitch_midi 列を抽出して返す
    """
    if not csv_path.exists() or not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    midi_notes: list[int] = []
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader, None)
        if not header:
            return midi_notes

        try:
            pitch_index = header.index("pitch_midi")
        except ValueError as error:
            raise ValueError(
                f"'pitch_midi' column not found in CSV: {csv_path}"
            ) from error

        for row in reader:
            if len(row) <= pitch_index:
                continue
            pitch_text = row[pitch_index].strip()
            if not pitch_text:
                continue
            try:
                midi_notes.append(int(float(pitch_text)))
            except ValueError:
                continue

    return midi_notes


def analyze_chord_from_csv(csv_path: Path) -> str:
    midi_notes = extract_pitch_midi_from_csv(csv_path)
    return analyze_chord(midi_notes)


def analyze_chord_from_midi_notes(midi_notes: list[int]) -> str:
    return analyze_chord(midi_notes)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect chord name from basic-pitch CSV (pitch_midi)."
    )
    parser.add_argument("csv_path", type=Path, help="Path to basic-pitch CSV file")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    chord_name = analyze_chord_from_csv(args.csv_path)
    print(chord_name)


# ==========================================
# 🧪 動作テスト
# ==========================================
if __name__ == "__main__":
    main()
