from __future__ import annotations

from dataclasses import replace

import sounddevice as sd

from code_generator import GuitarCodeGenerator
from detection_code import analyze_chord_from_csv, analyze_chord_from_midi_notes
from onset_live_basic_pitch import CONFIG, AnalysisResult, AttackStrokeRecognizer


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
    config = replace(
        CONFIG,
        quiet=True,
        show_input_devices_on_start=False,
        monitor_input=True,
        output_device=output_device,
    )

    generator = GuitarCodeGenerator("code_mapping.json")

    def _on_result(result: AnalysisResult) -> None:
        print(
            f"[Debug] 音量: RMS={result.rms_dbfs:.1f} dBFS / Peak={result.peak_dbfs:.1f} dBFS",
            flush=True,
        )
        if result.csv_path is not None:
            chord_name = analyze_chord_from_csv(result.csv_path)
        else:
            chord_name = analyze_chord_from_midi_notes(result.midi_notes)

        if chord_name and chord_name != "None":
            print(f"🎵 ギターのコード: {chord_name}", flush=True)
            generator.receive_chord(chord_name)

    recognizer = AttackStrokeRecognizer(config=config, on_result=_on_result)

    print("\n🎸 ライブコーディング待機中... ギターを弾いてください！(終了は Ctrl+C)")
    recognizer.run_forever()

    final_script = generator.get_final_script()
    output_path = "output_script.py"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_script)

    print("\n✅ ギタープログラミング終了！")
    print(f"✅ 生成されたスクリプトを `{output_path}` に保存しました。")


if __name__ == "__main__":
    main()
