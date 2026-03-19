from __future__ import annotations

import time
import sys
import subprocess
from pathlib import Path

import sounddevice as sd

from gui_pipeline import GuitarCodingPipeline, PipelineSettings


def _list_output_devices() -> list[tuple[int, str]]:
    devices = sd.query_devices()
    output_devices: list[tuple[int, str]] = []
    print("Available output devices:", flush=True)
    for idx, device in enumerate(devices):
        if device["max_output_channels"] > 0:
            name = str(device["name"])
            output_devices.append((idx, name))
            print(f"  [{idx}] {name} (out={device['max_output_channels']})", flush=True)
    if not output_devices:
        print("  (no output-capable devices found)", flush=True)
    return output_devices


def _choose_output_device() -> str | None:
    output_devices = _list_output_devices()
    try:
        selected = input(
            "Select output device index/name (Enter for system default): "
        ).strip()
    except EOFError:
        return None

    if not selected:
        return None

    if selected.isdigit():
        selected_index = int(selected)
        for device_index, device_name in output_devices:
            if device_index == selected_index:
                return device_name
        print(
            f"Output device index {selected_index} not found. Using system default.",
            flush=True,
        )
        return None

    return selected


def main() -> None:
    output_device = _choose_output_device()
    pipeline = GuitarCodingPipeline(
        mapping_file_path="code_mapping.json",
        output_path=Path("output_script.py"),
    )
    settings = PipelineSettings(
        output_device=output_device,
        monitor_input=True,
        quiet=True,
        show_input_devices_on_start=False,
    )

    print("\n🎸 ライブコーディング待機中... ギターを弾いてください！(終了は Ctrl+C)")
    pipeline.start(settings)

    try:
        while pipeline.is_running:
            event = pipeline.get_event_nowait()
            if event is None:
                time.sleep(0.05)
                continue

            if event.kind == "analysis":
                if event.rms_dbfs is not None and event.peak_dbfs is not None:
                    print(
                        f"[Debug] 音量: RMS={event.rms_dbfs:.1f} dBFS / Peak={event.peak_dbfs:.1f} dBFS",
                        flush=True,
                    )
                if event.chord_name and event.chord_name != "None":
                    print(f"🎵 ギターのコード: {event.chord_name}", flush=True)
                continue

            if event.kind == "error":
                print(f"[Error] {event.message}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.stop()

    output_path = pipeline.save_script()

    print("\n✅ ギタープログラミング終了！")
    print(f"✅ 生成されたスクリプトを `{output_path}` に保存しました。")

    # --- 修正箇所（ここから追加） ---
    print("\n" + "="*50)
    print("🚀 引き続き、自動でプログラムを実行します...")
    try:
        subprocess.run(
            [sys.executable, "run_guitar_code.py"],
            check=True
        )
    except FileNotFoundError:
        print("❌ エラー: `run_guitar_code.py` が見つかりません。同じフォルダに作成してください。")
    except Exception as e:
        print(f"❌ 自動実行中にエラーが発生しました: {e}")
    # --- 修正箇所（ここまで） ---


if __name__ == "__main__":
    main()
