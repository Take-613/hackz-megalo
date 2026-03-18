NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# 辞書：ルート音からの半音の距離（インターバル）の組み合わせ
CHORD_DICTIONARY = {
    (0, 4, 7): "Major",          # ルート, 長3度, 完全5度
    (0, 3, 7): "Minor",          # ルート, 短3度, 完全5度
    (0, 7): "Power",             # ルート, 完全5度 (パワーコード)
    (0, 4, 7, 10): "7th",        # ルート, 長3度, 完全5度, 短7度
    (0, 4, 7, 11): "Major 7th",  # ルート, 長3度, 完全5度, 長7度
    (0, 3, 7, 10): "Minor 7th",  # ルート, 短3度, 完全5度, 短7度
    (0, 5, 7): "sus4",           # ルート, 完全4度, 完全5度
    (0, 2, 4, 7): "add9",        # ルート, 長2度(9th), 長3度, 完全5度
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

# ==========================================
# 🧪 動作テスト
# ==========================================
if __name__ == "__main__":
    print("▼ テスト: Cメジャー (ド・ミ・ソ)")
    print(f"入力: [60, 64, 67] -> 出力: {analyze_chord([60, 64, 67])}\n")

    print("▼ テスト: Cメジャー (オクターブ違いが混ざった実際のギターの押さえ方)")
    print(f"入力: [48, 52, 55, 60, 64] -> 出力: {analyze_chord([48, 52, 55, 60, 64])}\n")

    print("▼ テスト: Gパワーコード (ソ・レ)")
    print(f"入力: [43, 50, 55] -> 出力: {analyze_chord([43, 50, 55])}\n")

    print("▼ テスト: 単音のD (レ)")
    print(f"入力: [62] -> 出力: {analyze_chord([62])}\n")
    
    print("▼ テスト: 辞書にない適当なノイズの塊")
    print(f"入力: [60, 61, 62] -> 出力: {analyze_chord([60, 61, 62])}\n")