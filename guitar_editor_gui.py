from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

import sounddevice as sd
import ttkbootstrap as tb

from gui_pipeline import GuitarCodingPipeline, PipelineEvent, PipelineSettings
from onset_live_basic_pitch import CONFIG
from run_guitar_code import execute_generated_script


CHORD_FINGERINGS: dict[tuple[str, str], tuple[str | int, ...]] = {
    ("C", "Major"): ("x", 3, 2, 0, 1, 0),
    ("C", "Minor"): ("x", 3, 5, 5, 4, 3),
    ("C", "7th"): ("x", 3, 2, 3, 1, 0),
    ("C", "Major 7th"): ("x", 3, 2, 0, 0, 0),
    ("C", "Minor 7th"): ("x", 3, 5, 3, 4, 3),
    ("C", "sus4"): ("x", 3, 3, 0, 1, 1),
    ("C", "add9"): ("x", 3, 2, 0, 3, 0),
    ("C", "Power"): ("x", 3, 5, 5, "x", "x"),
    ("C#", "Major"): ("x", 4, 6, 6, 6, 4),
    ("C#", "Minor"): ("x", 4, 6, 6, 5, 4),
    ("C#", "7th"): ("x", 4, 6, 4, 6, 4),
    ("C#", "Major 7th"): ("x", 4, 6, 5, 6, 4),
    ("C#", "Minor 7th"): ("x", 4, 6, 4, 5, 4),
    ("C#", "sus4"): ("x", 4, 6, 6, 7, 4),
    ("C#", "add9"): ("x", 4, 6, 6, 4, 4),
    ("C#", "Power"): ("x", 4, 6, 6, "x", "x"),
    ("D", "Major"): ("x", "x", 0, 2, 3, 2),
    ("D", "Minor"): ("x", "x", 0, 2, 3, 1),
    ("D", "7th"): ("x", "x", 0, 2, 1, 2),
    ("D", "Major 7th"): ("x", "x", 0, 2, 2, 2),
    ("D", "Minor 7th"): ("x", "x", 0, 2, 1, 1),
    ("D", "sus4"): ("x", "x", 0, 2, 3, 3),
    ("D", "add9"): ("x", "x", 0, 2, 3, 0),
    ("D", "Power"): ("x", 5, 7, 7, "x", "x"),
    ("D#", "Major"): ("x", 6, 8, 8, 8, 6),
    ("D#", "Minor"): ("x", 6, 8, 8, 7, 6),
    ("D#", "7th"): ("x", 6, 8, 6, 8, 6),
    ("D#", "Major 7th"): ("x", 6, 8, 7, 8, 6),
    ("D#", "Minor 7th"): ("x", 6, 8, 6, 7, 6),
    ("D#", "sus4"): ("x", 6, 8, 8, 9, 6),
    ("D#", "add9"): ("x", 6, 8, 8, 6, 6),
    ("D#", "Power"): ("x", 6, 8, 8, "x", "x"),
    ("E", "Major"): (0, 2, 2, 1, 0, 0),
    ("E", "Minor"): (0, 2, 2, 0, 0, 0),
    ("E", "7th"): (0, 2, 0, 1, 0, 0),
    ("E", "Major 7th"): (0, 2, 1, 1, 0, 0),
    ("E", "Minor 7th"): (0, 2, 0, 0, 0, 0),
    ("E", "sus4"): (0, 2, 2, 2, 0, 0),
    ("E", "add9"): (0, 2, 4, 1, 0, 0),
    ("E", "Power"): (0, 2, 2, "x", "x", "x"),
    ("F", "Major"): (1, 3, 3, 2, 1, 1),
    ("F", "Minor"): (1, 3, 3, 1, 1, 1),
    ("F", "7th"): (1, 3, 1, 2, 1, 1),
    ("F", "Major 7th"): ("x", "x", 3, 2, 1, 0),
    ("F", "Minor 7th"): (1, 3, 1, 1, 1, 1),
    ("F", "sus4"): (1, 3, 3, 3, 1, 1),
    ("F", "add9"): (1, 3, 0, 2, 1, 3),
    ("F", "Power"): (1, 3, 3, "x", "x", "x"),
    ("F#", "Major"): (2, 4, 4, 3, 2, 2),
    ("F#", "Minor"): (2, 4, 4, 2, 2, 2),
    ("F#", "7th"): (2, 4, 2, 3, 2, 2),
    ("F#", "Major 7th"): (2, 4, 3, 3, 2, 2),
    ("F#", "Minor 7th"): (2, 4, 2, 2, 2, 2),
    ("F#", "sus4"): (2, 4, 4, 4, 2, 2),
    ("F#", "add9"): (2, 4, 6, 3, 2, 2),
    ("F#", "Power"): (2, 4, 4, "x", "x", "x"),
    ("G", "Major"): (3, 2, 0, 0, 0, 3),
    ("G", "Minor"): (3, 5, 5, 3, 3, 3),
    ("G", "7th"): (3, 2, 0, 0, 0, 1),
    ("G", "Major 7th"): (3, 2, 0, 0, 0, 2),
    ("G", "Minor 7th"): (3, 5, 3, 3, 3, 3),
    ("G", "sus4"): (3, 3, 0, 0, 1, 3),
    ("G", "add9"): (3, 2, 0, 2, 0, 3),
    ("G", "Power"): (3, 5, 5, "x", "x", "x"),
    ("G#", "Major"): (4, 6, 6, 5, 4, 4),
    ("G#", "Minor"): (4, 6, 6, 4, 4, 4),
    ("G#", "7th"): (4, 6, 4, 5, 4, 4),
    ("G#", "Major 7th"): (4, 6, 5, 5, 4, 4),
    ("G#", "Minor 7th"): (4, 6, 4, 4, 4, 4),
    ("G#", "sus4"): (4, 6, 6, 6, 4, 4),
    ("G#", "add9"): (4, 6, 8, 5, 4, 4),
    ("G#", "Power"): (4, 6, 6, "x", "x", "x"),
    ("A", "Major"): ("x", 0, 2, 2, 2, 0),
    ("A", "Minor"): ("x", 0, 2, 2, 1, 0),
    ("A", "7th"): ("x", 0, 2, 0, 2, 0),
    ("A", "Major 7th"): ("x", 0, 2, 1, 2, 0),
    ("A", "Minor 7th"): ("x", 0, 2, 0, 1, 0),
    ("A", "sus4"): ("x", 0, 2, 2, 3, 0),
    ("A", "add9"): ("x", 0, 2, 4, 2, 0),
    ("A", "Power"): ("x", 0, 2, 2, "x", "x"),
    ("A#", "Major"): ("x", 1, 3, 3, 3, 1),
    ("A#", "Minor"): ("x", 1, 3, 3, 2, 1),
    ("A#", "7th"): ("x", 1, 3, 1, 3, 1),
    ("A#", "Major 7th"): ("x", 1, 3, 2, 3, 1),
    ("A#", "Minor 7th"): ("x", 1, 3, 1, 2, 1),
    ("A#", "sus4"): ("x", 1, 3, 3, 4, 1),
    ("A#", "add9"): ("x", 1, 3, 3, 1, 1),
    ("A#", "Power"): ("x", 1, 3, 3, "x", "x"),
    ("B", "Major"): ("x", 2, 4, 4, 4, 2),
    ("B", "Minor"): ("x", 2, 4, 4, 3, 2),
    ("B", "7th"): ("x", 2, 1, 2, 0, 2),
    ("B", "Major 7th"): ("x", 2, 4, 3, 4, 2),
    ("B", "Minor 7th"): ("x", 2, 4, 2, 3, 2),
    ("B", "sus4"): ("x", 2, 4, 4, 5, 2),
    ("B", "add9"): ("x", 2, 4, 4, 2, 2),
    ("B", "Power"): ("x", 2, 4, 4, "x", "x"),
}


class GuitarEditorApp:
    def __init__(self, root: tb.Window) -> None:
        self.root = root
        self.root.title("ChordCoder Studio")
        self.root.geometry("1280x820")

        self.pipeline = GuitarCodingPipeline()
        self._input_device_map: dict[str, int | None] = {}
        self._output_device_map: dict[str, int | None] = {}

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
        self.detected_chord_var = tk.StringVar(value="Detected Chord: -")
        self.level_var = tk.StringVar(value="RMS: -, Peak: -")
        self.paths_var = tk.StringVar(value="csv: (保存しない), midi: (保存しない)")
        self.rms_meter_var = tk.DoubleVar(value=0.0)
        self.peak_meter_var = tk.DoubleVar(value=0.0)
        self._chord_history: list[str] = []

        self._apply_theme()
        self._build_ui()
        self._reload_devices()
        self._set_editor_text(self.pipeline.get_script_text())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_events)

    def _apply_theme(self) -> None:
        self.root.configure(bg="#0F1117")
        style = self.root.style
        style.theme_use("darkly")

        palette = {
            "bg": "#1E1E1E",
            "panel": "#252526",
            "border": "#3C3C3C",
            "text": "#D4D4D4",
            "muted": "#9DA5B4",
            "accent": "#0E639C",
            "accent_hover": "#1177BB",
            "warn": "#A1260D",
            "warn_hover": "#C74E39",
            "editor": "#1E1E1E",
            "editor_text": "#D4D4D4",
            "console_bg": "#1F1F1F",
            "console_text": "#B5CEA8",
            "stream_bg": "#1B2B45",
            "stream_text": "#DCEBFF",
        }

        self.root.configure(bg=palette["bg"])

        style.configure("TFrame", background=palette["bg"])
        style.configure(
            "TLabel",
            background=palette["bg"],
            foreground=palette["text"],
            font=("Segoe UI", 11),
        )
        style.configure(
            "TLabelframe",
            background=palette["panel"],
            foreground=palette["muted"],
            borderwidth=1,
            relief="solid",
            bordercolor=palette["border"],
        )
        style.configure(
            "TLabelframe.Label",
            background=palette["panel"],
            foreground=palette["muted"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "TButton",
            padding=(10, 6),
            font=("Segoe UI", 10, "bold"),
            background=palette["panel"],
            foreground=palette["text"],
            bordercolor=palette["border"],
        )
        style.map(
            "TButton",
            background=[("active", "#2D2D2D")],
            foreground=[("active", "#FFFFFF")],
        )
        style.configure(
            "Accent.TButton",
            padding=(10, 6),
            font=("Segoe UI", 10, "bold"),
            background=palette["accent"],
            foreground="#FFFFFF",
            bordercolor=palette["accent"],
        )
        style.map(
            "Accent.TButton",
            background=[("active", palette["accent_hover"])],
            foreground=[("active", "#FFFFFF")],
        )
        style.configure(
            "Warn.TButton",
            padding=(10, 6),
            font=("Segoe UI", 10, "bold"),
            background=palette["warn"],
            foreground="#FFFFFF",
            bordercolor=palette["warn"],
        )
        style.map(
            "Warn.TButton",
            background=[("active", palette["warn_hover"])],
            foreground=[("active", "#FFFFFF")],
        )
        style.configure(
            "TEntry",
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            font=("Segoe UI", 11),
            borderwidth=1,
            bordercolor=palette["border"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            font=("Segoe UI", 10),
            bordercolor=palette["border"],
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=palette["panel"],
            background="#22C55E",
            bordercolor=palette["border"],
        )
        style.configure(
            "Status.TLabel",
            background=palette["bg"],
            foreground="#4FC1FF",
            font=("Segoe UI", 11, "bold"),
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(outer, text="Transport", padding=8)
        control_frame.pack(fill=tk.X)

        self.start_button = ttk.Button(
            control_frame, text="開始", command=self._start, style="Accent.TButton"
        )
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

        run_button = ttk.Button(
            control_frame, text="実行", command=self._run_script, style="Accent.TButton"
        )
        run_button.pack(side=tk.LEFT, padx=(8, 0))

        clear_button = ttk.Button(
            control_frame, text="クリア", command=self._clear, style="Warn.TButton"
        )
        clear_button.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(control_frame, text="  入力").pack(side=tk.LEFT, padx=(16, 2))
        self.device_combo = ttk.Combobox(
            control_frame,
            textvariable=self.input_device_var,
            state="readonly",
            width=24,
        )
        self.device_combo.pack(side=tk.LEFT)

        ttk.Label(control_frame, text="出力").pack(side=tk.LEFT, padx=(10, 2))
        self.output_device_combo = ttk.Combobox(
            control_frame,
            textvariable=self.output_device_var,
            state="readonly",
            width=24,
        )
        self.output_device_combo.pack(side=tk.LEFT)

        reload_button = ttk.Button(
            control_frame, text="再読込", command=self._reload_devices
        )
        reload_button.pack(side=tk.LEFT, padx=(8, 0))

        self.transport_status = ttk.Label(
            control_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
        )
        self.transport_status.pack(side=tk.RIGHT)

        content = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left_panel = ttk.LabelFrame(content, text="Guitar Input", padding=10)
        center_panel = ttk.Frame(content)
        right_panel = ttk.Panedwindow(content, orient=tk.VERTICAL)
        content.add(left_panel, weight=22)
        content.add(center_panel, weight=56)
        content.add(right_panel, weight=22)

        left_panel.columnconfigure(0, weight=1)

        ttk.Label(
            left_panel,
            textvariable=self.current_chord_var,
            font=("Helvetica", 30, "bold"),
            anchor="center",
        ).grid(row=0, column=0, sticky=tk.EW, pady=(0, 10))

        self.fretboard_canvas = tk.Canvas(
            left_panel,
            width=260,
            height=520,
            bg="#2B1F1A",
            highlightthickness=1,
            highlightbackground="#334155",
            relief=tk.FLAT,
        )
        self.fretboard_canvas.grid(row=1, column=0, sticky=tk.NSEW)
        self._draw_fretboard_base()

        ttk.Label(
            left_panel,
            textvariable=self.detected_chord_var,
            font=("Segoe UI", 13, "bold"),
            anchor="center",
            justify=tk.CENTER,
        ).grid(row=2, column=0, sticky=tk.EW, pady=(10, 2))

        level_block = ttk.Frame(left_panel)
        level_block.grid(row=3, column=0, sticky=tk.EW, pady=(6, 0))
        level_block.columnconfigure(0, weight=1)

        ttk.Label(level_block, text="RMS", font=("Helvetica", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W
        )
        self.rms_meter = ttk.Progressbar(
            level_block,
            orient=tk.HORIZONTAL,
            length=250,
            variable=self.rms_meter_var,
            maximum=100,
            mode="determinate",
        )
        self.rms_meter.grid(row=1, column=0, sticky=tk.EW)

        ttk.Label(level_block, text="Peak", font=("Helvetica", 11, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.peak_meter = ttk.Progressbar(
            level_block,
            orient=tk.HORIZONTAL,
            length=250,
            variable=self.peak_meter_var,
            maximum=100,
            mode="determinate",
        )
        self.peak_meter.grid(row=3, column=0, sticky=tk.EW)

        ttk.Label(left_panel, textvariable=self.level_var, font=("Helvetica", 11)).grid(
            row=4, column=0, sticky=tk.W, pady=(6, 0)
        )
        ttk.Label(left_panel, textvariable=self.paths_var, font=("Helvetica", 10)).grid(
            row=5, column=0, sticky=tk.W, pady=(2, 0)
        )

        center_panel.columnconfigure(0, weight=1)
        center_panel.rowconfigure(0, weight=3)
        center_panel.rowconfigure(1, weight=1)

        editor_frame = ttk.LabelFrame(center_panel, text="Code Editor", padding=8)
        editor_frame.grid(row=0, column=0, sticky=tk.NSEW)

        stream_frame = ttk.LabelFrame(center_panel, text="Chord Stream", padding=8)
        stream_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(10, 0))
        stream_frame.columnconfigure(0, weight=1)

        output_frame = ttk.LabelFrame(right_panel, text="Output", padding=8)
        variables_frame = ttk.LabelFrame(right_panel, text="Variables", padding=8)
        right_panel.add(output_frame, weight=1)
        right_panel.add(variables_frame, weight=1)

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
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="#4FC1FF",
            selectbackground="#264F78",
            selectforeground="#D4D4D4",
            font=("Consolas", 14),
            padx=10,
            pady=8,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.editor.pack(fill=tk.BOTH, expand=True)

        self.log = ScrolledText(
            output_frame,
            wrap=tk.WORD,
            height=8,
            state=tk.DISABLED,
            bg="#1F1F1F",
            fg="#B5CEA8",
            insertbackground="#4FC1FF",
            font=("Consolas", 12),
            padx=8,
            pady=6,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

        self.variables_box = ScrolledText(
            variables_frame,
            wrap=tk.WORD,
            height=8,
            state=tk.DISABLED,
            bg="#1F1F1F",
            fg="#D4D4D4",
            insertbackground="#4FC1FF",
            font=("Consolas", 12),
            padx=8,
            pady=6,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.variables_box.pack(fill=tk.BOTH, expand=True)

        self.chord_chip_row = ttk.Frame(stream_frame)
        self.chord_chip_row.grid(row=0, column=0, sticky=tk.W)

        self.stream_snippet = ScrolledText(
            stream_frame,
            wrap=tk.WORD,
            height=5,
            state=tk.DISABLED,
            bg="#1B2B45",
            fg="#DCEBFF",
            insertbackground="#4FC1FF",
            font=("Consolas", 12),
            padx=8,
            pady=6,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.stream_snippet.grid(row=1, column=0, sticky=tk.NSEW, pady=(8, 0))

        self._update_variables_box()

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
                self._input_device_map[input_label] = index
            if device["max_output_channels"] > 0:
                output_label = f"[{index}] {name}"
                output_items.append(output_label)
                self._output_device_map[output_label] = index

        self.device_combo["values"] = input_items
        self.output_device_combo["values"] = output_items

        if self.input_device_var.get() not in input_items:
            self.input_device_var.set("System default")
        if self.output_device_var.get() not in output_items:
            self.output_device_var.set("System default")

        if CONFIG.output_device:
            for label in self._output_device_map:
                if str(CONFIG.output_device).lower() in label.lower():
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
            self._set_output_next_action(
                title="取り込み開始",
                steps=[
                    "ギターを1回ストロークしてコードを検出してください",
                    "コードが検出されるとエディタへ自動反映されます",
                    "必要に応じて保存または実行を押してください",
                ],
            )
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
            self._set_output_next_action(
                title="保存完了",
                steps=[
                    f"保存先: {output_path}",
                    "内容を確認して問題なければ『実行』を押してください",
                    "続きを入力する場合はそのまま演奏を続けてください",
                ],
            )
            self.status_var.set("保存完了")
        except Exception as error:
            messagebox.showerror("保存エラー", str(error))

    def _run_script(self) -> None:
        try:
            output_path = self.pipeline.save_script(Path("output_script.py"))
            ok, message = execute_generated_script(str(output_path))
            if ok:
                self._set_output_next_action(
                    title="実行成功",
                    steps=[
                        f"実行ファイル: {output_path}",
                        "続けてコーディングする場合は再度ストロークしてください",
                        "現状を固定するなら保存して終了できます",
                    ],
                )
            else:
                self._set_output_next_action(
                    title="実行エラー",
                    steps=[
                        "生成コードを確認してください",
                        f"詳細: {message}",
                        "必要ならクリアして再入力してください",
                    ],
                )
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
        self.detected_chord_var.set("Detected Chord: -")
        self.level_var.set("RMS: -, Peak: -")
        self.paths_var.set("csv: (保存しない), midi: (保存しない)")
        self.rms_meter_var.set(0.0)
        self.peak_meter_var.set(0.0)
        self._chord_history.clear()
        self._render_chord_stream()
        self._set_stream_snippet(
            self._format_message(kind="status", raw_message="エディター表示をクリアしました。")
        )
        self._draw_fretboard_base()
        self._update_variables_box()

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
            self.detected_chord_var.set(self._build_chord_formula(event.chord_name))
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
            if event.chord_name and event.chord_name != "None":
                self._push_chord_stream(event.chord_name)
            self._update_fretboard(event.chord_name)
            if event.next_action_message and event.next_action_choices:
                self._set_output_next_menu(
                    menu_message=event.next_action_message,
                    choices=event.next_action_choices,
                )
            elif event.snippet:
                self._set_output_next_action(
                    title="入力反映",
                    steps=[
                        f"検出: {event.chord_name or 'None'}",
                        f"追加: {event.snippet}",
                        "次のコードを弾いて入力を続けてください",
                    ],
                )
            else:
                self._set_output_next_action(
                    title="コード解析完了",
                    steps=[
                        f"検出: {event.chord_name or 'None'}",
                        "このコードは現在のルールに未対応です",
                        "別のコードを弾くか、マッピングを追加してください",
                    ],
                )
            self._set_stream_snippet(
                self._format_message(
                    kind="analysis",
                    chord_name=event.chord_name,
                    snippet=event.snippet,
                    timestamp=event.timestamp,
                )
            )
            self._update_variables_box()
            return

        if event.kind == "error":
            self.status_var.set("エラー")
            self._set_output_next_action(
                title="エラー発生",
                steps=[
                    "入力デバイスと音量を確認してください",
                    "『デバイス再読込』後に再度開始してください",
                    f"詳細: {event.message}",
                ],
            )
            self._set_stream_snippet(
                self._format_message(kind="error", raw_message=event.message)
            )
            self._update_variables_box()
            return

        self._set_output_next_action(
            title="ステータス更新",
            steps=[
                event.message,
                "次の操作を続けてください",
            ],
        )
        self._set_stream_snippet(
            self._format_message(kind="status", raw_message=event.message)
        )
        self._update_variables_box()

    def _set_editor_text(self, text: str) -> None:
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", text)

    def _set_output_next_action(self, *, title: str, steps: list[str]) -> None:
        formatted = [f"▶ {title}"]
        for index, step in enumerate(steps, start=1):
            formatted.append(f"  {index}. {step}")

        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.insert("1.0", "\n".join(formatted))
        self.log.configure(state=tk.DISABLED)

    def _set_output_next_menu(
        self,
        *,
        menu_message: str,
        choices: list[tuple[str, str]],
    ) -> None:
        title = self._extract_menu_title(menu_message)
        lines = [f"┌ {title} ┐"]
        for chord_name, label in choices:
            lines.append(f"[ {chord_name} ] : {label}")
        lines.append("次に押すコードを1つ選んで弾いてください。")

        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.insert("1.0", "\n".join(lines))
        self.log.configure(state=tk.DISABLED)

    @staticmethod
    def _extract_menu_title(message: str) -> str:
        if "[" in message and "]" in message:
            left = message.find("[")
            right = message.find("]", left + 1)
            if left != -1 and right != -1:
                inner = message[left + 1 : right].strip()
                if inner:
                    return inner
        return message.strip() or "次のアクション"

    def _push_chord_stream(self, chord_name: str) -> None:
        self._chord_history.append(chord_name)
        self._chord_history = self._chord_history[-8:]
        self._render_chord_stream()

    def _render_chord_stream(self) -> None:
        for child in self.chord_chip_row.winfo_children():
            child.destroy()

        if not self._chord_history:
            ttk.Label(self.chord_chip_row, text="(no chords yet)").pack(side=tk.LEFT)
            return

        for index, chord_name in enumerate(self._chord_history):
            chip = tk.Label(
                self.chord_chip_row,
                text=chord_name,
                bg="#1E293B",
                fg="#BFDBFE",
                padx=10,
                pady=4,
                font=("Segoe UI", 10, "bold"),
                relief=tk.GROOVE,
                bd=1,
            )
            chip.pack(side=tk.LEFT, padx=(0, 6))
            if index < len(self._chord_history) - 1:
                arrow = ttk.Label(
                    self.chord_chip_row,
                    text="→",
                    font=("Segoe UI", 12, "bold"),
                    foreground="#60A5FA",
                )
                arrow.pack(side=tk.LEFT, padx=(0, 6))

    def _set_stream_snippet(self, text: str) -> None:
        self.stream_snippet.configure(state=tk.NORMAL)
        self.stream_snippet.delete("1.0", tk.END)
        self.stream_snippet.insert("1.0", text)
        self.stream_snippet.configure(state=tk.DISABLED)

    def _format_message(
        self,
        *,
        kind: str,
        chord_name: str | None = None,
        snippet: str | None = None,
        raw_message: str | None = None,
        timestamp: str | None = None,
    ) -> str:
        if kind == "analysis":
            lines = ["[解析結果]"]
            lines.append(f"・検出コード: {chord_name or 'None'}")

            chord_formula = self._build_chord_formula(chord_name)
            if chord_formula != "Detected Chord: -":
                lines.append(
                    f"・構成音: {chord_formula.replace('Detected Chord: ', '')}"
                )

            if snippet:
                lines.append("・反映内容: 生成コードへ追加しました")
                lines.append("・追加スニペット:")
                lines.append(f"    {snippet}")
            else:
                lines.append("・反映内容: 対応ルールがないため追加はありません")

            if timestamp:
                lines.append(f"・時刻: {timestamp}")
            return "\n".join(lines)

        if kind == "error":
            return "\n".join(
                [
                    "[エラー]",
                    "・処理中に問題が発生しました",
                    f"・詳細: {raw_message or '不明なエラー'}",
                    "・対処: デバイス設定と入力音量を確認してください",
                ]
            )

        status = raw_message or "待機中"
        if "開始" in status:
            summary = "取り込みを開始しました"
        elif "停止" in status:
            summary = "取り込みを停止しました"
        elif "保存" in status:
            summary = "スクリプトを保存しました"
        elif "実行" in status:
            summary = "スクリプトを実行しました"
        elif "クリア" in status:
            summary = "表示と履歴をクリアしました"
        else:
            summary = status

        return "\n".join(["[ステータス]", f"・{summary}", f"・詳細: {status}"])

    def _draw_fretboard_base(self) -> None:
        self.fretboard_canvas.delete("all")
        width = int(self.fretboard_canvas["width"])
        height = int(self.fretboard_canvas["height"])

        self.fretboard_canvas.create_rectangle(0, 0, width, height, fill="#3A241B", outline="")

        left = 28
        right = width - 28
        top = 20
        bottom = height - 32
        self._fretboard_geometry = (left, right, top, bottom)
        self._string_x_positions = [
            left + (right - left) * (string_index / 5) for string_index in range(6)
        ]
        self._fret_y_positions = [
            top + (bottom - top) * (fret_index / 7) for fret_index in range(8)
        ]

        self.fretboard_canvas.create_rectangle(
            left - 6, top - 12, right + 6, top - 4, fill="#E5D4B1", outline=""
        )

        for string_index in range(6):
            x = self._string_x_positions[string_index]
            self.fretboard_canvas.create_line(
                x,
                top,
                x,
                bottom,
                fill="#EFEFEF",
                width=1 + (string_index // 2),
            )

        for fret_index in range(1, 8):
            y = self._fret_y_positions[fret_index]
            self.fretboard_canvas.create_line(
                left, y, right, y, fill="#B7B7B7", width=2
            )

            if fret_index in (3, 5, 7):
                self.fretboard_canvas.create_oval(
                    (left + right) / 2 - 4,
                    y - (self._fret_y_positions[1] - top) / 2 - 4,
                    (left + right) / 2 + 4,
                    y - (self._fret_y_positions[1] - top) / 2 + 4,
                    fill="#E6D2A3",
                    outline="",
                )

    def _update_fretboard(self, chord_name: str | None) -> None:
        self._draw_fretboard_base()
        if not chord_name or chord_name == "None":
            return

        parts = chord_name.split(" ", 1)
        root = parts[0]
        chord_type = parts[1] if len(parts) > 1 else "Major"

        if chord_type == "Single":
            single_note_positions: dict[str, tuple[int, int]] = {
                "C": (1, 3),
                "C#": (1, 4),
                "D": (1, 5),
                "D#": (1, 6),
                "E": (0, 0),
                "F": (0, 1),
                "F#": (0, 2),
                "G": (0, 3),
                "G#": (0, 4),
                "A": (0, 5),
                "A#": (0, 6),
                "B": (0, 7),
            }
            pos = single_note_positions.get(root)
            if pos is None:
                return
            shape_list: list[str | int] = ["x", "x", "x", "x", "x", "x"]
            shape_list[pos[0]] = pos[1]
            shape: tuple[str | int, ...] = tuple(shape_list)
        else:
            shape = CHORD_FINGERINGS.get((root, chord_type))

        if shape is None:
            return

        fretted_values = [value for value in shape if isinstance(value, int) and value > 0]
        base_fret = min(fretted_values) if fretted_values else 1
        if base_fret < 1:
            base_fret = 1

        left, right, top, _ = self._fretboard_geometry
        if base_fret > 1:
            self.fretboard_canvas.create_text(
                left - 18,
                (self._fret_y_positions[1] + top) / 2,
                text=str(base_fret),
                fill="#F5E8C5",
                font=("Helvetica", 12, "bold"),
            )

        for string_index, value in enumerate(shape):
            x = self._string_x_positions[string_index]
            if value == "x":
                self.fretboard_canvas.create_text(
                    x,
                    top - 16,
                    text="x",
                    fill="#E8E8E8",
                    font=("Helvetica", 11, "bold"),
                )
                continue

            if value == 0:
                self.fretboard_canvas.create_oval(
                    x - 5,
                    top - 20,
                    x + 5,
                    top - 10,
                    outline="#E8E8E8",
                    width=2,
                )
                continue

            if isinstance(value, int):
                display_fret = value - base_fret + 1
                if not 1 <= display_fret <= 7:
                    continue

                y_top = self._fret_y_positions[display_fret - 1]
                y_bottom = self._fret_y_positions[display_fret]
                y = (y_top + y_bottom) / 2

                self.fretboard_canvas.create_oval(
                    x - 14,
                    y - 14,
                    x + 14,
                    y + 14,
                    fill="#38BDF8",
                    outline="#E0F2FE",
                    width=1,
                )

    def _build_chord_formula(self, chord_name: str | None) -> str:
        if not chord_name or chord_name == "None":
            return "Detected Chord: -"

        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        intervals_map = {
            "Single": [0],
            "Major": [0, 4, 7],
            "Minor": [0, 3, 7],
            "Power": [0, 7],
            "7th": [0, 4, 7, 10],
            "Major 7th": [0, 4, 7, 11],
            "Minor 7th": [0, 3, 7, 10],
            "sus4": [0, 5, 7],
            "add9": [0, 2, 4, 7],
        }

        parts = chord_name.split(" ", 1)
        if not parts:
            return f"Detected Chord: {chord_name}"

        root = parts[0]
        chord_type = parts[1] if len(parts) > 1 else ""
        if root not in note_names or chord_type not in intervals_map:
            return f"Detected Chord: {chord_name}"

        root_index = note_names.index(root)
        notes = [note_names[(root_index + interval) % 12] for interval in intervals_map[chord_type]]
        return f"Detected Chord: {root} ({'-'.join(notes)})"

    def _update_variables_box(self) -> None:
        lines = [
            f"status: {self.status_var.get()}",
            f"current_chord: {self.current_chord_var.get()}",
            f"{self.level_var.get()}",
            f"{self.paths_var.get()}",
        ]
        self.variables_box.configure(state=tk.NORMAL)
        self.variables_box.delete("1.0", tk.END)
        self.variables_box.insert("1.0", "\n".join(lines))
        self.variables_box.configure(state=tk.DISABLED)

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
    root = tb.Window(themename="darkly")
    app = GuitarEditorApp(root)
    del app
    root.mainloop()


if __name__ == "__main__":
    main()
