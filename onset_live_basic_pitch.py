from __future__ import annotations

import datetime as dt
import queue
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import librosa
import numpy as np
import sounddevice as sd
from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
from basic_pitch.inference import Model, predict, save_note_events

PREFERRED_INPUT_DEVICE_NAME = "Steinberg UR22C"
FIXED_INPUT_CHANNELS = 2


@dataclass(frozen=True)
class AppConfig:
    output_dir: Path = Path("outputs")
    sample_rate: int = 44100
    blocksize: int = 1024
    device: str | None = None
    output_device: str | None = "WF-1000XM5"
    monitor_input: bool = True
    monitor_gain: float = 1.0
    show_input_devices_on_start: bool = True
    quiet: bool = False
    save_inference_outputs: bool = True

    capture_seconds: float = 1.0
    detect_window_seconds: float = 2.0
    min_trigger_interval: float = 0.3

    hop_length: int = 512
    onset_delta: float = 0.2
    onset_pre_max: int = 3
    onset_post_max: int = 3
    onset_pre_avg: int = 3
    onset_post_avg: int = 5
    onset_wait: int = 3

    min_rms_db: float = -55.0
    min_rms_rise_db: float = 6.0
    rms_gate_window_seconds: float = 0.05
    calibration_seconds: float = 1.0
    print_level_stats: bool = False

    bp_onset_threshold: float = 0.5
    bp_frame_threshold: float = 0.3
    bp_minimum_note_length: float = 127.7
    bp_minimum_frequency: float | None = None
    bp_maximum_frequency: float | None = None
    bp_midi_tempo: float = 120.0


CONFIG = AppConfig()


@dataclass
class SegmentTask:
    index: int
    timestamp: str
    audio: np.ndarray
    sample_rate: int


@dataclass
class AnalysisResult:
    index: int
    timestamp: str
    midi_notes: list[int]
    midi_path: Path | None
    csv_path: Path | None
    note_count: int


ResultCallback = Callable[[AnalysisResult], None]


class BasicPitchWorker(threading.Thread):
    def __init__(
        self,
        *,
        task_queue: "queue.Queue[SegmentTask | None]",
        result_queue: "queue.Queue[AnalysisResult]",
        output_dir: Path,
        model: Model,
        onset_threshold: float,
        frame_threshold: float,
        minimum_note_length: float,
        minimum_frequency: float | None,
        maximum_frequency: float | None,
        midi_tempo: float,
        on_result: ResultCallback | None = None,
        quiet: bool = False,
        save_inference_outputs: bool = True,
    ) -> None:
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.output_dir = output_dir
        self.tmp_dir = output_dir / ".tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.onset_threshold = onset_threshold
        self.frame_threshold = frame_threshold
        self.minimum_note_length = minimum_note_length
        self.minimum_frequency = minimum_frequency
        self.maximum_frequency = maximum_frequency
        self.midi_tempo = midi_tempo
        self.on_result = on_result
        self.quiet = quiet
        self.save_inference_outputs = save_inference_outputs

    def run(self) -> None:
        while True:
            task = self.task_queue.get()
            if task is None:
                self.task_queue.task_done()
                return
            try:
                result = self._process(task)
                self.result_queue.put_nowait(result)
                if self.on_result is not None:
                    self.on_result(result)
            except Exception as error:
                if not self.quiet:
                    print(f"[Worker] analyze failed: {error}")
            finally:
                self.task_queue.task_done()

    def _process(self, task: SegmentTask) -> AnalysisResult:
        stem = f"attack_{task.timestamp}_{task.index:06d}"
        wav_path = self.tmp_dir / f"{stem}.wav"
        self._write_wav_mono(wav_path, task.audio, task.sample_rate)

        _, midi_data, note_events = predict(
            audio_path=wav_path,
            model_or_model_path=self.model,
            onset_threshold=self.onset_threshold,
            frame_threshold=self.frame_threshold,
            minimum_note_length=self.minimum_note_length,
            minimum_frequency=self.minimum_frequency,
            maximum_frequency=self.maximum_frequency,
            midi_tempo=self.midi_tempo,
        )

        midi_notes = [
            int(round(float(event[2])))
            for event in note_events
            if len(event) > 2
        ]

        midi_path: Path | None = None
        csv_path: Path | None = None
        if self.save_inference_outputs:
            midi_path = self.output_dir / f"{stem}_basic_pitch.mid"
            csv_path = self.output_dir / f"{stem}_basic_pitch.csv"
            midi_data.write(str(midi_path))
            save_note_events(note_events, csv_path)
            if not self.quiet:
                print(
                    f"[Worker] saved: {midi_path.name}, {csv_path.name} | notes={len(note_events)}"
                )
        elif not self.quiet:
            print(f"[Worker] inferred (no file save) | notes={len(note_events)}")

        try:
            wav_path.unlink(missing_ok=True)
        except OSError:
            pass

        return AnalysisResult(
            index=task.index,
            timestamp=task.timestamp,
            midi_notes=midi_notes,
            midi_path=midi_path,
            csv_path=csv_path,
            note_count=len(note_events),
        )

    @staticmethod
    def _write_wav_mono(path: Path, samples: np.ndarray, sample_rate: int) -> None:
        pcm = np.clip(samples, -1.0, 1.0)
        pcm = (pcm * np.iinfo(np.int16).max).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())


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


def resolve_output_device(device_arg: str | None) -> str | int | None:
    if device_arg is None:
        return None

    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device["max_output_channels"] <= 0:
            continue
        if str(device_arg).lower() in device["name"].lower():
            return idx

    return device_arg


def device_label(device: str | int | None, direction: str) -> str:
    if device is None:
        return "default"
    if isinstance(device, str):
        return device

    try:
        info = sd.query_devices(device)
    except Exception:
        return str(device)

    if direction == "input" and info["max_input_channels"] <= 0:
        return f"{info['name']} (not input-capable)"
    if direction == "output" and info["max_output_channels"] <= 0:
        return f"{info['name']} (not output-capable)"
    return str(info["name"])


def detect_attack_sample(
    *,
    signal: np.ndarray,
    sample_rate: int,
    hop_length: int,
    delta: float,
    pre_max: int,
    post_max: int,
    pre_avg: int,
    post_avg: int,
    wait: int,
    absolute_start_sample: int,
    last_trigger_sample: int,
    min_trigger_interval_samples: int,
) -> int | None:
    if len(signal) < hop_length * 4:
        return None

    onset_envelope = librosa.onset.onset_strength(
        y=signal,
        sr=sample_rate,
        hop_length=hop_length,
    )
    onset_samples = librosa.onset.onset_detect(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        hop_length=hop_length,
        units="samples",
        delta=delta,
        pre_max=pre_max,
        post_max=post_max,
        pre_avg=pre_avg,
        post_avg=post_avg,
        wait=wait,
    )
    if len(onset_samples) == 0:
        return None

    for sample in onset_samples:
        absolute_sample = int(absolute_start_sample + sample)
        if absolute_sample - last_trigger_sample >= min_trigger_interval_samples:
            return absolute_sample
    return None


def validate_config(config: AppConfig) -> None:
    if config.sample_rate <= 0:
        raise ValueError("--sample-rate must be positive")
    if config.blocksize <= 0:
        raise ValueError("--blocksize must be positive")
    if config.capture_seconds <= 0:
        raise ValueError("--capture-seconds must be positive")
    if config.detect_window_seconds <= 0:
        raise ValueError("--detect-window-seconds must be positive")
    if config.hop_length <= 0:
        raise ValueError("--hop-length must be positive")
    if config.min_trigger_interval < 0:
        raise ValueError("--min-trigger-interval must be >= 0")
    if config.calibration_seconds < 0:
        raise ValueError("--calibration-seconds must be >= 0")
    if config.rms_gate_window_seconds <= 0:
        raise ValueError("--rms-gate-window-seconds must be positive")
    if config.monitor_gain < 0:
        raise ValueError("monitor_gain must be >= 0")


def rms_dbfs(signal: np.ndarray) -> float:
    if len(signal) == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(signal))))
    return 20.0 * np.log10(max(rms, 1e-8))


class AttackStrokeRecognizer:
    def __init__(
        self,
        config: AppConfig = CONFIG,
        on_result: Optional[ResultCallback] = None,
    ) -> None:
        self.config = config
        validate_config(self.config)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        self.on_result = on_result
        self._result_queue: "queue.Queue[AnalysisResult]" = queue.Queue(maxsize=256)
        self._audio_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=256)
        self._stop_event = threading.Event()

        onnx_model_path = build_icassp_2022_model_path(FilenameSuffix.onnx)
        if not self.config.quiet:
            print(f"Loading basic-pitch model once: {onnx_model_path}")
        self._model = Model(onnx_model_path)

        self._task_queue: "queue.Queue[SegmentTask | None]" = queue.Queue(maxsize=16)
        self._worker = self._create_worker()

        self._stream: sd.InputStream | sd.Stream | None = None
        self._loop_thread: threading.Thread | None = None

        self._input_device = resolve_input_device(self.config.device)
        self._selected_device = device_label(self._input_device, "input")
        self._output_device = resolve_output_device(self.config.output_device)
        self._selected_output_device = device_label(self._output_device, "output")

        self._detect_window_samples = int(
            self.config.detect_window_seconds * self.config.sample_rate
        )
        self._capture_samples = int(
            self.config.capture_seconds * self.config.sample_rate
        )
        self._min_trigger_interval_samples = int(
            self.config.min_trigger_interval * self.config.sample_rate
        )
        self._calibration_samples = int(
            self.config.calibration_seconds * self.config.sample_rate
        )
        self._rms_gate_window_samples = max(
            1, int(self.config.rms_gate_window_seconds * self.config.sample_rate)
        )

        self._detect_buffer = np.zeros(0, dtype=np.float32)
        self._detect_buffer_start_sample = 0
        self._total_samples = 0
        self._last_trigger_sample = -(10**12)
        self._segment_index = 0
        self._noise_floor_db: float | None = None
        self._calibration_rms_values: list[float] = []
        self._printed_chunks = 0
        self._rejected_chunks = 0

        self._capturing = False
        self._capture_remaining = 0
        self._capture_parts: list[np.ndarray] = []

    @property
    def is_running(self) -> bool:
        return self._loop_thread is not None and self._loop_thread.is_alive()

    def _create_worker(self) -> BasicPitchWorker:
        return BasicPitchWorker(
            task_queue=self._task_queue,
            result_queue=self._result_queue,
            output_dir=self.config.output_dir,
            model=self._model,
            onset_threshold=self.config.bp_onset_threshold,
            frame_threshold=self.config.bp_frame_threshold,
            minimum_note_length=self.config.bp_minimum_note_length,
            minimum_frequency=self.config.bp_minimum_frequency,
            maximum_frequency=self.config.bp_maximum_frequency,
            midi_tempo=self.config.bp_midi_tempo,
            on_result=self.on_result,
            quiet=self.config.quiet,
            save_inference_outputs=self.config.save_inference_outputs,
        )

    def start(self) -> None:
        if self.is_running:
            return

        if self.config.show_input_devices_on_start:
            list_input_devices()

        self._stop_event.clear()
        if not self._worker.is_alive():
            self._task_queue = queue.Queue(maxsize=16)
            self._worker = self._create_worker()

        if not self.config.quiet:
            print(
                f"Input device={self._selected_device}, sr={self.config.sample_rate}, channels={FIXED_INPUT_CHANNELS}, blocksize={self.config.blocksize}"
            )
            print(f"Output device={self._selected_output_device}")
            if self.config.monitor_input:
                print(
                    f"Input monitor=ON, output_device={self._selected_output_device}, gain={self.config.monitor_gain:.2f}"
                )
            print("Model is ready. Start listening...")

        self._worker.start()
        if self.config.monitor_input:
            self._stream = sd.Stream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.blocksize,
                dtype="float32",
                channels=(FIXED_INPUT_CHANNELS, FIXED_INPUT_CHANNELS),
                callback=self._audio_output_callback,
                device=(self._input_device, self._output_device),
            )
        else:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=FIXED_INPUT_CHANNELS,
                dtype="float32",
                blocksize=self.config.blocksize,
                callback=self._audio_callback,
                device=self._input_device,
            )
        self._stream.start()

        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop()
            finally:
                self._stream.close()
            self._stream = None

        if self._loop_thread is not None:
            self._loop_thread.join(timeout=3)
            self._loop_thread = None

        self._task_queue.put(None)
        self._worker.join(timeout=10)
        if not self.config.quiet:
            print("Stopped")

    def run_forever(self) -> None:
        self.start()
        try:
            while self.is_running:
                self._stop_event.wait(timeout=0.5)
                if self._stop_event.is_set():
                    break
        except KeyboardInterrupt:
            if not self.config.quiet:
                print("\nStopping...")
        finally:
            self.stop()

    def get_result(self, timeout: float | None = None) -> AnalysisResult | None:
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
    ) -> None:
        del frames, time_info
        if status:
            if not self.config.quiet:
                print(f"[Audio] {status}")
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        try:
            self._audio_queue.put_nowait(mono.astype(np.float32, copy=True))
        except queue.Full:
            if not self.config.quiet:
                print("[Audio] queue overflow: input chunk dropped")

    def _audio_output_callback(
        self,
        indata: np.ndarray,
        outdata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        self._audio_callback(indata, frames, time_info, status)
        mono = indata.mean(axis=1, keepdims=True)
        outdata[:] = mono * self.config.monitor_gain

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._process_chunk(chunk)

    def _process_chunk(self, chunk: np.ndarray) -> None:
        chunk_start = self._total_samples
        chunk_end = chunk_start + len(chunk)
        self._total_samples = chunk_end
        chunk_rms_db = rms_dbfs(chunk)

        if self._total_samples <= self._calibration_samples:
            self._calibration_rms_values.append(chunk_rms_db)
            if self.config.print_level_stats and self._printed_chunks % 30 == 0:
                print(f"[Calib] chunk_rms={chunk_rms_db:.1f}dBFS (collecting)")
            self._printed_chunks += 1
            return

        if self._noise_floor_db is None:
            if self._calibration_rms_values:
                self._noise_floor_db = float(np.median(self._calibration_rms_values))
            else:
                self._noise_floor_db = chunk_rms_db
            if not self.config.quiet:
                print(
                    f"[Calib] done: noise_floor={self._noise_floor_db:.1f}dBFS "
                    f"from first {self.config.calibration_seconds:.2f}s"
                )

        if self.config.print_level_stats:
            self._printed_chunks += 1
            if self._printed_chunks % 30 == 0:
                print(
                    f"[Level] chunk_rms={chunk_rms_db:.1f}dBFS noise_floor={self._noise_floor_db:.1f}dBFS"
                )

        self._detect_buffer = np.concatenate((self._detect_buffer, chunk))
        if len(self._detect_buffer) > self._detect_window_samples:
            trim = len(self._detect_buffer) - self._detect_window_samples
            self._detect_buffer = self._detect_buffer[trim:]
            self._detect_buffer_start_sample += trim

        if not self._capturing:
            gate_signal = self._detect_buffer[-self._rms_gate_window_samples :]
            gate_rms_db = rms_dbfs(gate_signal)
            gate_abs_ok = gate_rms_db >= self.config.min_rms_db
            gate_rise_ok = (
                gate_rms_db >= self._noise_floor_db + self.config.min_rms_rise_db
            )
            if not gate_abs_ok or not gate_rise_ok:
                self._rejected_chunks += 1
                if self.config.print_level_stats and self._rejected_chunks % 30 == 0:
                    print(
                        f"[Gate] reject rms={gate_rms_db:.1f}dBFS floor={self._noise_floor_db:.1f}dBFS "
                        f"(need >= {self.config.min_rms_db:.1f} and >= floor+{self.config.min_rms_rise_db:.1f})"
                    )
                return

            attack_sample = detect_attack_sample(
                signal=self._detect_buffer,
                sample_rate=self.config.sample_rate,
                hop_length=self.config.hop_length,
                delta=self.config.onset_delta,
                pre_max=self.config.onset_pre_max,
                post_max=self.config.onset_post_max,
                pre_avg=self.config.onset_pre_avg,
                post_avg=self.config.onset_post_avg,
                wait=self.config.onset_wait,
                absolute_start_sample=self._detect_buffer_start_sample,
                last_trigger_sample=self._last_trigger_sample,
                min_trigger_interval_samples=self._min_trigger_interval_samples,
            )
            if attack_sample is not None:
                self._capture_remaining = self._capture_samples
                self._capture_parts = []
                self._capturing = True
                self._last_trigger_sample = attack_sample

                offset = max(0, attack_sample - chunk_start)
                if offset < len(chunk):
                    sliced = chunk[offset:]
                else:
                    sliced = np.zeros(0, dtype=np.float32)

                take = sliced[: self._capture_remaining]
                if len(take) > 0:
                    self._capture_parts.append(take)
                    self._capture_remaining -= len(take)

                attack_sec = attack_sample / self.config.sample_rate
                if not self.config.quiet:
                    print(
                        f"[Detect] attack at {attack_sec:.3f}s -> capture start | "
                        f"rms={gate_rms_db:.1f}dBFS floor={self._noise_floor_db:.1f}dBFS"
                    )

        else:
            take = chunk[: self._capture_remaining]
            if len(take) > 0:
                self._capture_parts.append(take)
                self._capture_remaining -= len(take)

        if self._capturing and self._capture_remaining <= 0:
            segment = np.concatenate(self._capture_parts, axis=0)
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            task = SegmentTask(
                index=self._segment_index,
                timestamp=timestamp,
                audio=segment,
                sample_rate=self.config.sample_rate,
            )
            self._segment_index += 1

            try:
                self._task_queue.put_nowait(task)
                if not self.config.quiet:
                    print(
                        f"[Queue] segment #{task.index} queued ({self.config.capture_seconds:.2f}s)"
                    )
            except queue.Full:
                if not self.config.quiet:
                    print("[Queue] worker queue is full: segment dropped")

            self._capturing = False
            self._capture_remaining = 0
            self._capture_parts = []


def main() -> None:
    recognizer = AttackStrokeRecognizer(CONFIG)
    recognizer.run_forever()


if __name__ == "__main__":
    main()
