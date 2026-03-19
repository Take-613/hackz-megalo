from __future__ import annotations

import queue
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Lock

from code_generator import GuitarCodeGenerator
from detection_code import analyze_chord_from_csv, analyze_chord_from_midi_notes
from onset_live_basic_pitch import (
    CONFIG,
    AnalysisResult,
    AppConfig,
    AttackStrokeRecognizer,
)


@dataclass(frozen=True)
class PipelineSettings:
    input_device: str | None = None
    output_device: str | None = CONFIG.output_device
    monitor_input: bool = True
    quiet: bool = True
    show_input_devices_on_start: bool = False
    onset_delta: float = CONFIG.onset_delta
    min_rms_db: float = CONFIG.min_rms_db
    min_rms_rise_db: float = CONFIG.min_rms_rise_db
    capture_seconds: float = CONFIG.capture_seconds
    min_trigger_interval: float = CONFIG.min_trigger_interval
    bp_onset_threshold: float = CONFIG.bp_onset_threshold
    bp_frame_threshold: float = CONFIG.bp_frame_threshold
    bp_minimum_note_length: float = CONFIG.bp_minimum_note_length
    bp_midi_tempo: float = CONFIG.bp_midi_tempo


@dataclass(frozen=True)
class PipelineEvent:
    kind: str
    message: str
    timestamp: str | None = None
    chord_name: str | None = None
    snippet: str | None = None
    script_text: str | None = None
    csv_path: str | None = None
    midi_path: str | None = None
    rms_dbfs: float | None = None
    peak_dbfs: float | None = None


class GuitarCodingPipeline:
    def __init__(
        self,
        *,
        mapping_file_path: str = "code_mapping.json",
        output_path: Path = Path("output_script.py"),
        output_dir: Path = Path("outputs"),
    ) -> None:
        self.output_path = output_path
        self.output_dir = output_dir
        self._generator = GuitarCodeGenerator(
            mapping_file_path=mapping_file_path,
            render_terminal=False,
        )
        self._recognizer: AttackStrokeRecognizer | None = None
        self._events: queue.Queue[PipelineEvent] = queue.Queue(maxsize=512)
        self._lock = Lock()

    @property
    def is_running(self) -> bool:
        return self._recognizer is not None and self._recognizer.is_running

    def start(self, settings: PipelineSettings) -> None:
        if self.is_running:
            return

        config = self._build_config(settings)
        self._recognizer = AttackStrokeRecognizer(
            config=config, on_result=self._on_result
        )
        self._recognizer.start()
        self._push_event(
            PipelineEvent(kind="status", message="取り込みを開始しました。")
        )

    def stop(self) -> None:
        if self._recognizer is None:
            return

        self._recognizer.stop()
        self._recognizer = None
        self._push_event(
            PipelineEvent(kind="status", message="取り込みを停止しました。")
        )

    def clear_script(self) -> None:
        with self._lock:
            self._generator.generated_lines.clear()
            script_text = self._generator.get_final_script()
        self._push_event(
            PipelineEvent(
                kind="status",
                message="エディター表示をクリアしました。",
                script_text=script_text,
            )
        )

    def save_script(self, output_path: Path | None = None) -> Path:
        target = output_path or self.output_path
        with self._lock:
            script_text = self._generator.get_final_script()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(script_text, encoding="utf-8")
        self._push_event(
            PipelineEvent(
                kind="status",
                message=f"スクリプトを保存しました: {target}",
                script_text=script_text,
            )
        )
        return target

    def get_script_text(self) -> str:
        with self._lock:
            return self._generator.get_final_script()

    def get_event_nowait(self) -> PipelineEvent | None:
        try:
            return self._events.get_nowait()
        except queue.Empty:
            return None

    def _on_result(self, result: AnalysisResult) -> None:
        try:
            if result.csv_path is not None:
                chord_name = analyze_chord_from_csv(result.csv_path)
            else:
                chord_name = analyze_chord_from_midi_notes(result.midi_notes)

            snippet: str | None = None
            with self._lock:
                if chord_name and chord_name != "None":
                    snippet = self._generator.code_mapping.get(chord_name)
                    self._generator.receive_chord(chord_name)
                script_text = self._generator.get_final_script()

            self._push_event(
                PipelineEvent(
                    kind="analysis",
                    message="解析結果を受信しました。",
                    timestamp=result.timestamp,
                    chord_name=chord_name,
                    snippet=snippet,
                    script_text=script_text,
                    csv_path=str(result.csv_path) if result.csv_path else None,
                    midi_path=str(result.midi_path) if result.midi_path else None,
                    rms_dbfs=result.rms_dbfs,
                    peak_dbfs=result.peak_dbfs,
                )
            )
        except Exception as error:
            self._push_event(PipelineEvent(kind="error", message=str(error)))

    def _push_event(self, event: PipelineEvent) -> None:
        try:
            self._events.put_nowait(event)
        except queue.Full:
            pass

    def _build_config(self, settings: PipelineSettings) -> AppConfig:
        return replace(
            CONFIG,
            output_dir=self.output_dir,
            save_inference_outputs=False,
            device=settings.input_device,
            output_device=settings.output_device,
            monitor_input=settings.monitor_input,
            quiet=settings.quiet,
            show_input_devices_on_start=settings.show_input_devices_on_start,
            onset_delta=settings.onset_delta,
            min_rms_db=settings.min_rms_db,
            min_rms_rise_db=settings.min_rms_rise_db,
            capture_seconds=settings.capture_seconds,
            min_trigger_interval=settings.min_trigger_interval,
            bp_onset_threshold=settings.bp_onset_threshold,
            bp_frame_threshold=settings.bp_frame_threshold,
            bp_minimum_note_length=settings.bp_minimum_note_length,
            bp_midi_tempo=settings.bp_midi_tempo,
        )
