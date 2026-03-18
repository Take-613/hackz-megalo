# hacks-megalo

`sounddevice` でマイク音声を録音し、そのまま `basic-pitch` に流して MIDI/CSV を出力できます。

## 前提

- Python 3.11+
- `uv` がインストール済み

## 使い方

### 1) 既存音声ファイルを解析

任意の音声ファイル（wav/mp3/flac など）を指定します。

```bash
uv run python device-test.py path/to/input.wav --output-dir outputs
```

### 2) マイク録音してそのまま解析

```bash
uv run python device-test.py --record-seconds 10 --output-dir outputs
```

録音したWAVはテスト用として、デフォルトで `test_recordings/` に保存されます。
保存先を変える場合は `--test-audio-dir` か `--record-output` を指定してください。

### 3) 入力デバイス一覧を確認

```bash
uv run python device-test.py --list-devices
```

必要に応じて `--device`（名前またはインデックス）、`--sample-rate`、`--channels` を指定できます。

### 4) ヘルプ表示

```bash
uv run python device-test.py --help
```

## librosaでアタック検出して0.5秒だけ解析（常時監視）

`onset_live_basic_pitch.py` は以下を繰り返します。

- `librosa` でアタック（オンセット）を検出
- 検出地点から 0.5 秒だけ音声を切り出し
- 常駐した `basic-pitch` モデルで解析

`Ctrl+C` で止めるまで無限ループで動作します。

```bash
uv run python onset_live_basic_pitch.py
```

## リアルタイムで「コード名だけ」を出力する

`onset_live_basic_code.py` は以下を自動で連携します。

- ギター入力を `onset_live_basic_pitch.py` で取り込み
- 解析結果CSVの `pitch_midi` を `detection_code.py` で分類
- 標準出力にはコード名のみ（例: `E Major`）を表示

```bash
uv run python onset_live_basic_code.py
```

## 既存CSVからコード判定だけ実行する

```bash
uv run python detection_code.py outputs/xxx_basic_pitch.csv
```

他プログラムから組み込む場合:

```python
from onset_live_basic_pitch import AttackStrokeRecognizer, AppConfig

config = AppConfig(output_dir="outputs")
recognizer = AttackStrokeRecognizer(config)
recognizer.start()

# 別スレッド/ループで結果を取り出す
result = recognizer.get_result(timeout=1.0)
if result:
	print(result.csv_path, result.midi_path, result.note_count)

# 終了時
recognizer.stop()
```

各種パラメータ（感度、ノイズ閾値、デバイス、保存先など）は
`onset_live_basic_pitch.py` の `CONFIG = AppConfig(...)` を編集して調整します。

入力デバイス確認（起動時に表示したい場合）:

`show_input_devices_on_start=True` に設定。

主な調整パラメータ:

- `onset_delta`（アタック検出の感度）
- `min_trigger_interval`（連続トリガの最小間隔秒）
- `device`（入力デバイス名またはインデックス）
- `monitor_input`（入力音をそのまま出力して自分で聴く）
- `monitor_gain`（モニター音量）
- `output_device`（モニター出力デバイス）
- `min_rms_db` / `min_rms_rise_db`（誤検出抑制ゲート）

誤検出が多い場合の例:

`capture_seconds=0.5`, `min_rms_db=-55`, `min_rms_rise_db=6`,
`calibration_seconds=1.0`, `onset_delta=0.2` を `CONFIG` に設定。

`calibration_seconds` で指定した起動直後（例: 1秒）の無演奏音量をノイズ床として固定し、
その基準に対して `min_rms_rise_db` 以上立ち上がったときだけアタック判定します。

必要に応じて `print_level_stats=True` で入力レベルとノイズ床を確認できます。
