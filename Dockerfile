# basic-pitchの依存関係（TensorFlowなど）を考慮し、安定しているPython 3.11を採用
FROM python:3.11-slim

# 音声ファイルの読み込み・変換に必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 公式イメージから uv をコピー（推奨されている最速のインストール方法）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 作業ディレクトリの設定
WORKDIR /app

# コンテナを起動し続けるためのコマンド（開発用）
CMD ["tail", "-f", "/dev/null"]