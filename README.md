# hacks-megalo

`sounddevice` でマイク音声を録音し、そのまま `basic-pitch` に流して MIDI/CSV を出力できます。

## 使い方

### 1) 既存音声ファイルを解析

```bash
uv run python main.py music/canon-normal.wav --output-dir outputs
```

### 2) マイク録音してそのまま解析

```bash
uv run python main.py --record-seconds 10 --output-dir outputs
```

録音したWAVはテスト用として、デフォルトで `test_recordings/` に保存されます。
保存先を変える場合は `--test-audio-dir` か `--record-output` を指定してください。

### 3) 入力デバイス一覧を確認

```bash
uv run python main.py --list-devices
```

必要に応じて `--device`（名前またはインデックス）、`--sample-rate`、`--channels` を指定できます。

## テスト用コマンド

`pyproject.toml` にコマンドを登録済みです。

```bash
uv run megalo-audio-test --record-seconds 10 --output-dir outputs
```

ヘルプ表示:

```bash
uv run megalo-audio-test --help
```
