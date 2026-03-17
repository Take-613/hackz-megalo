from __future__ import annotations

import argparse
import datetime as dt
import wave
from pathlib import Path

import numpy as np
import pretty_midi
import sounddevice as sd
from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
from basic_pitch.inference import predict, save_note_events

PREFERRED_INPUT_DEVICE_NAME = "Steinberg UR22C"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze audio with basic-pitch (from file or live microphone recording)."
    )
    parser.add_argument(
        "audio_path",
        type=Path,
        nargs="?",
        help="Input audio file path (wav/mp3/flac etc.)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory to save analysis result files",
    )
    parser.add_argument("--onset-threshold", type=float, default=0.5)
    parser.add_argument("--frame-threshold", type=float, default=0.3)
    parser.add_argument(
        "--minimum-note-length", type=float, default=127.70, help="milliseconds"
    )
    parser.add_argument("--minimum-frequency", type=float, default=None)
    parser.add_argument("--maximum-frequency", type=float, default=None)
    parser.add_argument("--midi-tempo", type=float, default=120.0)
    parser.add_argument(
        "--record-seconds",
        type=float,
        default=None,
        help="Record from microphone for N seconds, then analyze",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Sample rate for microphone recording",
    )
    parser.add_argument(
        "--channels", type=int, default=2, help="Recording channel count"
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Input device name or index for sounddevice",
    )
    parser.add_argument(
        "--record-output",
        type=Path,
        default=None,
        help="Path to save recorded wav file (if omitted, saved under --test-audio-dir)",
    )
    parser.add_argument(
        "--test-audio-dir",
        type=Path,
        default=Path("test_recordings"),
        help="Directory to keep recorded wav files for testing",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )
    return parser


def list_input_devices() -> None:
    devices = sd.query_devices()
    print("Available input devices:")
    for idx, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            print(
                f"  [{idx}] {device['name']} (in={device['max_input_channels']}, out={device['max_output_channels']})"
            )


def resolve_input_device(device_arg: str | None) -> str | int | None:
    if device_arg is not None:
        return device_arg

    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device["max_input_channels"] <= 0:
            continue
        if PREFERRED_INPUT_DEVICE_NAME.lower() in device["name"].lower():
            return idx

    return None


def record_microphone_to_wav(args: argparse.Namespace) -> Path:
    if args.record_seconds is None or args.record_seconds <= 0:
        raise ValueError("--record-seconds must be a positive number")
    if args.sample_rate <= 0:
        raise ValueError("--sample-rate must be positive")
    if args.channels <= 0:
        raise ValueError("--channels must be positive")

    args.test_audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.record_output
    if output_path is None:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = args.test_audio_dir / f"mic_{timestamp}.wav"

    frames = int(args.record_seconds * args.sample_rate)
    if frames <= 0:
        raise ValueError("recording duration too short")

    input_device = resolve_input_device(args.device)
    selected_device_label = args.device or PREFERRED_INPUT_DEVICE_NAME
    if input_device is None:
        selected_device_label = "default"

    print(
        f"Recording: {args.record_seconds:.2f}s @ {args.sample_rate}Hz, channels={args.channels}, device={selected_device_label}"
    )
    recording = sd.rec(
        frames,
        samplerate=args.sample_rate,
        channels=args.channels,
        dtype="float32",
        device=input_device,
    )
    sd.wait()

    mono = recording.mean(axis=1) if args.channels > 1 else recording.ravel()
    pcm = np.clip(mono, -1.0, 1.0)
    pcm = (pcm * np.iinfo(np.int16).max).astype(np.int16)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(args.sample_rate)
        wav_file.writeframes(pcm.tobytes())

    print(f"Recorded WAV: {output_path}")
    return output_path


def resolve_audio_source(args: argparse.Namespace) -> Path:
    if args.audio_path is not None and args.record_seconds is not None:
        raise ValueError("Specify either audio_path or --record-seconds, not both")

    if args.audio_path is not None:
        return args.audio_path

    if args.record_seconds is not None:
        return record_microphone_to_wav(args)

    raise ValueError("Provide audio_path or --record-seconds")


def analyze_and_export(args: argparse.Namespace) -> None:
    source_audio_path = resolve_audio_source(args)
    if not source_audio_path.exists() or not source_audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {source_audio_path}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    onnx_model_path = build_icassp_2022_model_path(FilenameSuffix.onnx)

    _, midi_data, note_events = predict(
        audio_path=source_audio_path,
        model_or_model_path=onnx_model_path,
        onset_threshold=args.onset_threshold,
        frame_threshold=args.frame_threshold,
        minimum_note_length=args.minimum_note_length,
        minimum_frequency=args.minimum_frequency,
        maximum_frequency=args.maximum_frequency,
        midi_tempo=args.midi_tempo,
    )

    stem = source_audio_path.stem
    midi_path = args.output_dir / f"{stem}_basic_pitch.mid"
    csv_path = args.output_dir / f"{stem}_basic_pitch.csv"

    midi_data.write(str(midi_path))
    save_note_events(note_events, csv_path)

    print(f"Saved MIDI: {midi_path}")
    print(f"Saved note events CSV: {csv_path}")
    print(f"Model backend: ONNX ({onnx_model_path})")

    note_count = len(note_events)
    duration_sec = max((event[1] for event in note_events), default=0.0)
    print(f"Detected notes: {note_count}")
    print(f"Estimated duration: {duration_sec:.2f}s")

    if note_events:
        print("Top 10 note events:")
        for start_time, end_time, pitch_midi, velocity, _ in note_events[:10]:
            note_name = pretty_midi.note_number_to_name(pitch_midi)
            print(
                f"  {start_time:.2f}s - {end_time:.2f}s | {note_name} ({pitch_midi}) | velocity={int(round(127 * velocity))}"
            )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.list_devices:
        list_input_devices()
        return
    analyze_and_export(args)


if __name__ == "__main__":
    main()
