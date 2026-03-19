from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import sounddevice as sd

from gui_pipeline import GuitarCodingPipeline, PipelineEvent, PipelineSettings
from onset_live_basic_pitch import CONFIG
from run_guitar_code import execute_generated_script


class GuitarEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Guitar Code Editor - DTM Layout")
        self.root.geometry("1280x820")

        self.pipeline = GuitarCodingPipeline()
        self._input_device_map: dict[str, str | None] = {}
        self._output_device_map: dict[str, str | None] = {}

        self.input_device_var = tk.StringVar(value="System default")
        self.output_device_var = tk.StringVar(value="System default")
        self.onset_delta_var = tk.StringVar(value=str(CONFIG.onset_delta))
        self.min_rms_db_var = tk.StringVar(value=str(CONFIG.min_rms_db))
        self.min_rms_rise_db_var = tk.StringVar(value=str(CONFIG.min_rms_rise_db))
        self.capture_seconds_var = tk.StringVar(value=str(CONFIG.capture_seconds))
        self.min_trigger_interval_var = tk.StringVar(
            value=str(CONFIG.min_trigger_interval)
        )
        self.bp_onset_threshold_var = tk.StringVar(value=str(CONFIG.bp_onset_threshold))
        self.bp_frame_threshold_var = tk.StringVar(value=str(CONFIG.bp_frame_threshold))
        self.bp_minimum_note_length_var = tk.StringVar(
            value=str(CONFIG.bp_minimum_note_length)
        )
        self.bp_midi_tempo_var = tk.StringVar(value=str(CONFIG.bp_midi_tempo))

        self.status_var = tk.StringVar(value="待機中")
        self.current_chord_var = tk.StringVar(value="-")
        self.level_var = tk.StringVar(value="RMS: -, Peak: -")
        self.paths_var = tk.StringVar(value="csv: (保存しない), midi: (保存しない)")
        self.rms_meter_var = tk.DoubleVar(value=0.0)
        self.peak_meter_var = tk.DoubleVar(value=0.0)

        self._apply_theme()
        self._build_ui()
        self._reload_devices()
        self._set_editor_text(self.pipeline.get_script_text())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_events)

    def _apply_theme(self) -> None:
        self.root.configure(bg="#1E1F22")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background="#1E1F22")
        style.configure("TLabel", background="#1E1F22", foreground="#E6E6E6")
        style.configure("TLabelframe", background="#1E1F22", foreground="#B8B8B8")
        style.configure("TLabelframe.Label", background="#1E1F22", foreground="#B8B8B8")
        style.configure("TButton", padding=6)
        style.configure("TEntry", fieldbackground="#2A2C31", foreground="#F0F0F0")
        style.configure("TCombobox", fieldbackground="#2A2C31", foreground="#F0F0F0")
        style.configure(
            "Horizontal.TProgressbar", troughcolor="#2A2C31", background="#00C853"
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(outer, text="Transport", padding=8)
        control_frame.pack(fill=tk.X)

        self.start_button = ttk.Button(control_frame, text="開始", command=self._start)
        self.start_button.pack(side=tk.LEFT)

        self.stop_button = ttk.Button(
            control_frame,
            text="停止",
            command=self._stop,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=(8, 0))

        save_button = ttk.Button(control_frame, text="保存", command=self._save)
        save_button.pack(side=tk.LEFT, padx=(8, 0))

        run_button = ttk.Button(control_frame, text="実行", command=self._run_script)
        run_button.pack(side=tk.LEFT, padx=(8, 0))

        clear_button = ttk.Button(control_frame, text="クリア", command=self._clear)
        clear_button.pack(side=tk.LEFT, padx=(8, 0))

        self.transport_status = ttk.Label(
            control_frame,
            textvariable=self.status_var,
            font=("Helvetica", 11, "bold"),
        )
        self.transport_status.pack(side=tk.RIGHT)

        content = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left_panel = ttk.Frame(content)
        right_panel = ttk.Frame(content)
        content.add(left_panel, weight=1)
        content.add(right_panel, weight=3)

        mixer_frame = ttk.LabelFrame(left_panel, text="Mixer", padding=8)
        mixer_frame.pack(fill=tk.X)

        ttk.Label(mixer_frame, text="現在のコード").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            mixer_frame,
            textvariable=self.current_chord_var,
            font=("Helvetica", 16, "bold"),
        ).grid(row=1, column=0, sticky=tk.W, pady=(2, 6))

        ttk.Label(mixer_frame, text="RMS").grid(row=2, column=0, sticky=tk.W)
        self.rms_meter = ttk.Progressbar(
            mixer_frame,
            orient=tk.HORIZONTAL,
            length=240,
            variable=self.rms_meter_var,
            maximum=100,
            mode="determinate",
        )
        self.rms_meter.grid(row=3, column=0, sticky=tk.EW)

        ttk.Label(mixer_frame, text="Peak").grid(
            row=4, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.peak_meter = ttk.Progressbar(
            mixer_frame,
            orient=tk.HORIZONTAL,
            length=240,
            variable=self.peak_meter_var,
            maximum=100,
            mode="determinate",
        )
        self.peak_meter.grid(row=5, column=0, sticky=tk.EW)

        ttk.Label(mixer_frame, textvariable=self.level_var).grid(
            row=6, column=0, sticky=tk.W, pady=(6, 0)
        )
        ttk.Label(mixer_frame, textvariable=self.paths_var).grid(
            row=7, column=0, sticky=tk.W, pady=(4, 0)
        )

        settings_frame = ttk.LabelFrame(
            left_panel, text="Device & Detection", padding=8
        )
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.device_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.input_device_var,
            state="readonly",
            width=30,
        )
        self.device_combo.grid(row=0, column=1, sticky=tk.W)

        self.output_device_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.output_device_var,
            state="readonly",
            width=30,
        )
        self.output_device_combo.grid(row=1, column=1, sticky=tk.W, pady=(4, 0))

        reload_button = ttk.Button(
            settings_frame, text="デバイス再読込", command=self._reload_devices
        )
        reload_button.grid(row=0, column=2, padx=(8, 0), sticky=tk.W)

        ttk.Label(settings_frame, text="入力デバイス").grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Label(settings_frame, text="出力デバイス").grid(
            row=1, column=0, sticky=tk.W, pady=(4, 0)
        )

        rows = [
            ("onset_delta", self.onset_delta_var),
            ("min_rms_db", self.min_rms_db_var),
            ("min_rms_rise_db", self.min_rms_rise_db_var),
            ("capture_seconds", self.capture_seconds_var),
            ("min_trigger_interval", self.min_trigger_interval_var),
            ("bp_onset_threshold", self.bp_onset_threshold_var),
            ("bp_frame_threshold", self.bp_frame_threshold_var),
            ("bp_minimum_note_length", self.bp_minimum_note_length_var),
            ("bp_midi_tempo", self.bp_midi_tempo_var),
        ]

        for index, (label, variable) in enumerate(rows, start=2):
            ttk.Label(settings_frame, text=label).grid(
                row=index, column=0, sticky=tk.W, pady=(4, 0)
            )
            entry = ttk.Entry(settings_frame, textvariable=variable, width=18)
            entry.grid(row=index, column=1, sticky=tk.W, pady=(4, 0))

        right_split = ttk.Panedwindow(right_panel, orient=tk.VERTICAL)
        right_split.pack(fill=tk.BOTH, expand=True)

        editor_frame = ttk.LabelFrame(
            right_split, text="Track Editor (Generated Code)", padding=8
        )
        log_frame = ttk.LabelFrame(right_split, text="Console", padding=8)
        right_split.add(editor_frame, weight=4)
        right_split.add(log_frame, weight=1)

        ruler = ttk.Label(
            editor_frame,
            text="Bar 1 | Bar 2 | Bar 3 | Bar 4",
            foreground="#A0A0A0",
        )
        ruler.pack(anchor=tk.W, pady=(0, 4))

        self.editor = ScrolledText(
            editor_frame,
            wrap=tk.NONE,
            height=24,
            bg="#17181B",
            fg="#EAEAEA",
            insertbackground="#FFFFFF",
            font=("Menlo", 14),
            padx=10,
            pady=8,
        )
        self.editor.pack(fill=tk.BOTH, expand=True)

        self.log = ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=8,
            state=tk.DISABLED,
            bg="#111214",
            fg="#CFE8CF",
            insertbackground="#FFFFFF",
            font=("Menlo", 11),
            padx=8,
            pady=6,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

    def _reload_devices(self) -> None:
        try:
            devices = sd.query_devices()
        except Exception as error:
            messagebox.showerror("デバイス読込エラー", str(error))
            return

        input_items = ["System default"]
        output_items = ["System default"]
        self._input_device_map = {"System default": None}
        self._output_device_map = {"System default": None}
        for index, device in enumerate(devices):
            name = str(device["name"])
            if device["max_input_channels"] > 0:
                input_label = f"[{index}] {name}"
                input_items.append(input_label)
                self._input_device_map[input_label] = name
            if device["max_output_channels"] > 0:
                output_label = f"[{index}] {name}"
                output_items.append(output_label)
                self._output_device_map[output_label] = name

        self.device_combo["values"] = input_items
        self.output_device_combo["values"] = output_items

        if self.input_device_var.get() not in input_items:
            self.input_device_var.set("System default")
        if self.output_device_var.get() not in output_items:
            self.output_device_var.set("System default")

        if CONFIG.output_device:
            for label, value in self._output_device_map.items():
                if value and str(CONFIG.output_device).lower() in value.lower():
                    if self.output_device_var.get() == "System default":
                        self.output_device_var.set(label)
                    break

    def _start(self) -> None:
        if self.pipeline.is_running:
            return

        try:
            settings = PipelineSettings(
                input_device=self._input_device_map.get(self.input_device_var.get()),
                output_device=self._output_device_map.get(self.output_device_var.get()),
                onset_delta=self._as_float(self.onset_delta_var, "onset_delta"),
                min_rms_db=self._as_float(self.min_rms_db_var, "min_rms_db"),
                min_rms_rise_db=self._as_float(
                    self.min_rms_rise_db_var, "min_rms_rise_db"
                ),
                capture_seconds=self._as_float(
                    self.capture_seconds_var, "capture_seconds"
                ),
                min_trigger_interval=self._as_float(
                    self.min_trigger_interval_var, "min_trigger_interval"
                ),
                bp_onset_threshold=self._as_float(
                    self.bp_onset_threshold_var, "bp_onset_threshold"
                ),
                bp_frame_threshold=self._as_float(
                    self.bp_frame_threshold_var, "bp_frame_threshold"
                ),
                bp_minimum_note_length=self._as_float(
                    self.bp_minimum_note_length_var, "bp_minimum_note_length"
                ),
                bp_midi_tempo=self._as_float(self.bp_midi_tempo_var, "bp_midi_tempo"),
            )
            self.pipeline.start(settings)
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.status_var.set("取り込み中")
            self._append_log("取り込みを開始しました。")
        except Exception as error:
            self.status_var.set("開始失敗")
            messagebox.showerror("開始エラー", str(error))

    def _stop(self) -> None:
        try:
            self.pipeline.stop()
        except Exception as error:
            messagebox.showerror("停止エラー", str(error))
        finally:
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)
            self.status_var.set("停止中")

    def _save(self) -> None:
        try:
            output_path = self.pipeline.save_script(Path("output_script.py"))
            self._append_log(f"保存: {output_path}")
            self.status_var.set("保存完了")
        except Exception as error:
            messagebox.showerror("保存エラー", str(error))

    def _run_script(self) -> None:
        try:
            output_path = self.pipeline.save_script(Path("output_script.py"))
            ok, message = execute_generated_script(str(output_path))
            self._append_log(f"実行: {output_path}")
            self._append_log(message)
            self.status_var.set("実行成功" if ok else "実行エラー")
            if ok:
                messagebox.showinfo("実行結果", message)
            else:
                messagebox.showerror("実行結果", message)
        except Exception as error:
            messagebox.showerror("実行エラー", str(error))

    def _clear(self) -> None:
        self.pipeline.clear_script()
        self.current_chord_var.set("-")
        self.level_var.set("RMS: -, Peak: -")
        self.paths_var.set("csv: (保存しない), midi: (保存しない)")
        self.rms_meter_var.set(0.0)
        self.peak_meter_var.set(0.0)

    def _poll_events(self) -> None:
        while True:
            event = self.pipeline.get_event_nowait()
            if event is None:
                break
            self._handle_event(event)

        self.root.after(100, self._poll_events)

    def _handle_event(self, event: PipelineEvent) -> None:
        if event.kind == "analysis":
            self.current_chord_var.set(event.chord_name or "None")
            if event.rms_dbfs is not None and event.peak_dbfs is not None:
                self.level_var.set(
                    f"RMS: {event.rms_dbfs:.1f} dBFS, Peak: {event.peak_dbfs:.1f} dBFS"
                )
                self.rms_meter_var.set(self._db_to_meter(event.rms_dbfs))
                self.peak_meter_var.set(self._db_to_meter(event.peak_dbfs))
            self.paths_var.set(
                f"csv: {event.csv_path or '(保存しない)'}, midi: {event.midi_path or '(保存しない)'}"
            )
            if event.script_text is not None:
                self._set_editor_text(event.script_text)
            suffix = f" | snippet: {event.snippet}" if event.snippet else ""
            self._append_log(
                f"{event.timestamp or '-'} | chord: {event.chord_name or 'None'}{suffix}"
            )
            return

        if event.kind == "error":
            self.status_var.set("エラー")
            self._append_log(f"ERROR: {event.message}")
            return

        self._append_log(event.message)

    def _set_editor_text(self, text: str) -> None:
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", text)

    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    @staticmethod
    def _db_to_meter(dbfs: float) -> float:
        clamped = max(-80.0, min(0.0, dbfs))
        return ((clamped + 80.0) / 80.0) * 100.0

    @staticmethod
    def _as_float(var: tk.StringVar, label: str) -> float:
        text = var.get().strip()
        try:
            return float(text)
        except ValueError as error:
            raise ValueError(f"{label} は数値で入力してください: {text}") from error

    def _on_close(self) -> None:
        if self.pipeline.is_running:
            self.pipeline.stop()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = GuitarEditorApp(root)
    del app
    root.mainloop()


if __name__ == "__main__":
    main()
