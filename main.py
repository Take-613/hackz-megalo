from __future__ import annotations

import argparse
from pathlib import Path

import pretty_midi
from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
from basic_pitch.inference import predict, save_note_events


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze an audio file with basic-pitch and export MIDI/CSV note events."
    )
    parser.add_argument(
        "audio_path", type=Path, help="Input audio file path (wav/mp3/flac etc.)"
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
    return parser


def analyze_and_export(args: argparse.Namespace) -> None:
    if not args.audio_path.exists() or not args.audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {args.audio_path}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    onnx_model_path = build_icassp_2022_model_path(FilenameSuffix.onnx)

    _, midi_data, note_events = predict(
        audio_path=args.audio_path,
        model_or_model_path=onnx_model_path,
        onset_threshold=args.onset_threshold,
        frame_threshold=args.frame_threshold,
        minimum_note_length=args.minimum_note_length,
        minimum_frequency=args.minimum_frequency,
        maximum_frequency=args.maximum_frequency,
        midi_tempo=args.midi_tempo,
    )

    stem = args.audio_path.stem
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
    analyze_and_export(args)


if __name__ == "__main__":
    main()
