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
