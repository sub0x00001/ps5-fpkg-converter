"""Tkinter front-end for PS5 FPKG Converter.

Layout: input package, output directory, output format, progress bar with a
scrolling log, and Start / Stop / Close buttons. The conversion itself runs in
a worker thread; the Tk main loop only drains a queue of log lines and
progress updates, so the window always stays responsive.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

from . import __version__
from . import engine

POLL_MS = 100


class ConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"PS5 FPKG Converter {__version__}")
        self.resizable(True, True)
        self.minsize(720, 480)

        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._job_lock = threading.Lock()
        self._current_job: Optional["_JobHandle"] = None

        self._build_widgets()
        self._set_running(False)
        self.after(POLL_MS, self._drain_queue)

    # ------------------------------------------------------------------ UI

    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}

        form = ttk.LabelFrame(self, text="Conversion")
        form.pack(fill="x", padx=10, pady=8)

        ttk.Label(form, text="Input package:").grid(row=0, column=0, sticky="w", **pad)
        self.input_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.input_var).grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(form, text="Browse...", command=self._pick_input).grid(row=0, column=2, **pad)

        ttk.Label(form, text="Output directory:").grid(row=1, column=0, sticky="w", **pad)
        self.output_var = tk.StringVar(value=str(Path.cwd()))
        ttk.Entry(form, textvariable=self.output_var).grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(form, text="Browse...", command=self._pick_output).grid(row=1, column=2, **pad)

        ttk.Label(form, text="Output format:").grid(row=2, column=0, sticky="w", **pad)
        self.format_var = tk.StringVar(value="folder")
        fmt_box = ttk.Combobox(
            form,
            textvariable=self.format_var,
            state="readonly",
            values=list(engine.OUTPUT_FORMATS),
            width=12,
        )
        fmt_box.grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(form, text="(folder dump, .ffpfs image, .ffpfsc compressed image)").grid(
            row=2, column=2, columnspan=2, sticky="w", **pad
        )

        self.sign_var = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Fake-sign executables (--sign)", variable=self.sign_var).grid(
            row=3, column=1, sticky="w", **pad
        )
        ttk.Checkbutton(form, text="Overwrite existing output", variable=self.overwrite_var).grid(
            row=3, column=2, sticky="w", **pad
        )
        form.columnconfigure(1, weight=1)

        progress = ttk.LabelFrame(self, text="Progress")
        progress.pack(fill="x", padx=10, pady=4)
        self.progress_bar = ttk.Progressbar(progress, maximum=100)
        self.progress_bar.pack(fill="x", padx=8, pady=(8, 0))
        self.progress_label = ttk.Label(progress, text="Idle.")
        self.progress_label.pack(fill="x", padx=8, pady=(0, 8))

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=4)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=12, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=10, pady=(4, 10))
        self.start_btn = ttk.Button(buttons, text="Start", command=self._on_start)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(buttons, text="Stop", command=self._on_stop)
        self.stop_btn.pack(side="left", padx=4)
        ttk.Button(buttons, text="Close", command=self._on_close).pack(side="right", padx=4)
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(buttons, textvariable=self.status_var).pack(side="left", padx=12)

    # ------------------------------------------------------------- helpers

    def _log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        if not running:
            self.progress_bar.configure(value=0)

    def _pick_input(self) -> None:
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Select a PS5 fake package",
            filetypes=[("PS5 package", "*.pkg"), ("All files", "*.*")],
        )
        if chosen:
            self.input_var.set(chosen)

    def _pick_output(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title="Select the output directory")
        if chosen:
            self.output_var.set(chosen)

    # ------------------------------------------------------------- actions

    def _on_start(self) -> None:
        input_path = Path(self.input_var.get().strip())
        output_dir = Path(self.output_var.get().strip())
        output_format = self.format_var.get()

        if not input_path.is_file():
            messagebox.showerror("Invalid input", f"Input package not found:\n{input_path}")
            return
        if input_path.suffix.lower() != ".pkg":
            if not messagebox.askyesno(
                "Unusual extension", "The input does not end in .pkg. Continue anyway?"
            ):
                return
        if engine.locate_tool() is None:
            messagebox.showerror(
                "Engine missing",
                "ffpfsc-pkg-tool was not found.\n\n"
                "Build it with scripts/build-engine.ps1 (requires the .NET 9 SDK) "
                "or set the FFPFSC_PKG_TOOL environment variable.",
            )
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        job = _JobHandle()
        with self._job_lock:
            self._current_job = job

        def emit(line: str) -> None:
            self._queue.put(("line", line))

        def work() -> None:
            try:
                code = engine.run_conversion(
                    input_path,
                    output_dir,
                    output_format,
                    sign=self.sign_var.get(),
                    overwrite=self.overwrite_var.get(),
                    on_line=emit,
                )
                self._queue.put(("done", code))
            except Exception as exc:  # surface anything unexpected to the UI
                self._queue.put(("error", str(exc)))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()
        self._set_running(True)
        self.status_var.set(f"Converting {input_path.name} -> {output_format}")
        self.progress_label.configure(text="Starting engine...")

    def _on_stop(self) -> None:
        with self._job_lock:
            job = self._current_job
        if job is not None and job.stop():
            self.status_var.set("Stopping (engine killed; scratch files may remain)...")
            self._log("[UI] stop requested")

    def _on_close(self) -> None:
        with self._job_lock:
            job = self._current_job
        if job is not None and not job.stopped:
            if not messagebox.askyesno("Conversion running", "A conversion is still running. Stop it and close?"):
                return
            job.stop()
        self.destroy()

    # -------------------------------------------------------------- events

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "line":
                    self._log(payload)
                    progress = engine.parse_progress(payload)
                    if progress:
                        percent, message = progress
                        self.progress_bar.configure(value=percent)
                        self.progress_label.configure(text=f"{percent}%  {message}")
                elif kind == "done":
                    self._finish(payload)
                elif kind == "error":
                    self._log(f"[ERROR] {payload}")
                    self._finish(1)
        except queue.Empty:
            pass
        self.after(POLL_MS, self._drain_queue)

    def _finish(self, code: int) -> None:
        with self._job_lock:
            self._current_job = None
        self._set_running(False)
        if code == 0:
            self.status_var.set("Done.")
            self.progress_label.configure(text="Conversion finished successfully.")
            self.progress_bar.configure(value=100)
            messagebox.showinfo("Finished", "Conversion finished successfully.")
        else:
            self.status_var.set(f"Failed (exit code {code}).")
            self.progress_label.configure(text="Conversion failed; check the log.")
            messagebox.showerror("Failed", f"The engine exited with code {code}.\nCheck the log for details.")


class _JobHandle:
    """Handle owned by the UI thread; engine.stop_job is called via the runner."""

    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> bool:
        if self.stopped:
            return False
        self.stopped = True
        engine.stop_running_job()
        return True


def main() -> int:
    app = ConverterApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
