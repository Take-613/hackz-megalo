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

## `AppConfig` パラメータ一覧

`onset_live_basic_pitch.py` の `CONFIG = AppConfig(...)` にある全パラメータです。

### 1) 入出力・実行設定

- `output_dir` (default: `Path("outputs")`): 推論結果（MIDI/CSV）や一時ファイル出力先。
- `sample_rate` (default: `44100`): 音声サンプリングレート（Hz）。
- `blocksize` (default: `1024`): オーディオコールバック1回あたりのフレーム数。
- `device` (default: `None`): 入力デバイス名またはインデックス。`None` は自動選択。
- `output_device` (default: `"WF-1000XM5"`): モニター出力先デバイス名またはインデックス。
- `monitor_input` (default: `True`): 入力音をそのまま出力へ流すかどうか。
- `monitor_gain` (default: `1.0`): モニター出力ゲイン。
- `show_input_devices_on_start` (default: `True`): 起動時に入力デバイス一覧を表示。
- `quiet` (default: `False`): ログ出力を抑制するかどうか。
- `save_inference_outputs` (default: `True`): Basic PitchのMIDI/CSVを保存するかどうか。

### 2) アタック検出・切り出し設定

- `capture_seconds` (default: `1.0`): アタック検出後に切り出して解析する音声長（秒）。
- `detect_window_seconds` (default: `2.0`): オンセット検出に使うリングバッファ長（秒）。
- `min_trigger_interval` (default: `0.3`): 連続トリガーの最小間隔（秒）。
- `hop_length` (default: `512`): `librosa` のオンセット検出ホップ長（サンプル）。
- `onset_delta` (default: `0.2`): オンセット検出の閾値（大きいほど反応しにくい）。
- `onset_pre_max` (default: `3`): ピーク検出の前方最大化フレーム数。
- `onset_post_max` (default: `3`): ピーク検出の後方最大化フレーム数。
- `onset_pre_avg` (default: `3`): 平均化に使う前方フレーム数。
- `onset_post_avg` (default: `5`): 平均化に使う後方フレーム数。
- `onset_wait` (default: `3`): 連続オンセット間で待機する最小フレーム数。

### 3) 音量ゲート・ノイズ床設定（誤検出抑制）

- `min_rms_db` (default: `-30.0`): 絶対RMSゲート閾値（dBFS）。
- `min_rms_rise_db` (default: `6.0`): ノイズ床に対する必要上昇量（dB）。
- `rms_gate_window_seconds` (default: `0.05`): ゲート判定に使う末尾窓長（秒）。
- `calibration_seconds` (default: `1.0`): 起動直後にノイズ床を学習する時間（秒）。
- `print_level_stats` (default: `False`): レベル統計ログ（RMS/ノイズ床）を表示。

### 4) Basic Pitch 推論設定

- `bp_onset_threshold` (default: `0.5`): Basic Pitchのオンセットしきい値。
- `bp_frame_threshold` (default: `0.3`): Basic Pitchのフレームしきい値。
- `bp_minimum_note_length` (default: `127.7`): 最小ノート長（ミリ秒）。
- `bp_minimum_frequency` (default: `None`): 推論対象の最小周波数（Hz）。
- `bp_maximum_frequency` (default: `None`): 推論対象の最大周波数（Hz）。
- `bp_midi_tempo` (default: `120.0`): 出力MIDIテンポ。

### 調整の目安

- 誤検出が多い場合: `min_rms_db` を上げる（例: `-30 -> -24`）、`min_rms_rise_db` を上げる。
- 取りこぼしが多い場合: `min_rms_db` を下げる、`onset_delta` を下げる。
- まず観測したい場合: `print_level_stats=True` で `chunk_rms` と `noise_floor` を確認。
