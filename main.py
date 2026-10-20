"""TradingView AutoBot - GUI entry point."""
import ctypes
import queue
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

# Make screen coordinates match on scaled (125% / 150%) Windows displays
if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import pyautogui  # noqa: E402

from bot.config import load_config, save_config  # noqa: E402
from bot.engine import BotEngine  # noqa: E402
from bot.hotkeys import HotkeyListener  # noqa: E402

CALIB_STEPS = [
    ("pine_editor_tab", "Hover the mouse over the 'Pine Editor' button in TradingView, then press F8."),
    ("pine_editor_text", "Open Pine Editor, hover over its CODE TEXT AREA, then press F8."),
    ("add_to_chart_button", "Hover over 'Add to chart' button and press F8  (or F9 to skip and use Ctrl+Enter)."),
]


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.q = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.calib_index = None

        self.hotkeys = HotkeyListener(on_esc=self.stop_event.set)
        self.hotkeys.on_other = lambda k: self.q.put(("key", k))
        self.hotkeys.start()

        root.title("TradingView AutoBot")
        root.geometry("620x480")
        root.attributes("-topmost", True)

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        self.btn_start = ttk.Button(top, text="▶ START", command=self.start)
        self.btn_start.pack(side="left", padx=3)
        ttk.Button(top, text="■ Stop (ESC)", command=self.stop_event.set).pack(side="left", padx=3)
        ttk.Button(top, text="Test analysis", command=self.test_analysis).pack(side="left", padx=3)
        ttk.Button(top, text="Calibrate", command=self.start_calibration).pack(side="left", padx=3)

        opts = ttk.LabelFrame(root, text="Options", padding=8)
        opts.pack(fill="x", padx=8)
        ttk.Label(opts, text="Strategy:").grid(row=0, column=0, sticky="w")
        self.mode = tk.StringVar(value="auto")
        ttk.Combobox(opts, textvariable=self.mode, values=["auto", "trend", "range"],
                     width=8, state="readonly").grid(row=0, column=1, sticky="w")
        self.add_builtin = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Add built-in indicator from Indicators menu",
                        variable=self.add_builtin).grid(row=0, column=2, sticky="w", padx=10)
        self.editor_open = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Pine Editor is already open",
                        variable=self.editor_open).grid(row=1, column=2, sticky="w", padx=10)
        self.monitor = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Keep monitoring, every (sec):",
                        variable=self.monitor).grid(row=1, column=0, columnspan=1, sticky="w")
        self.interval = tk.IntVar(value=self.cfg["monitor_interval_sec"])
        ttk.Spinbox(opts, from_=10, to=3600, textvariable=self.interval, width=6).grid(row=1, column=1, sticky="w")
        self.hide = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Minimize this window while running",
                        variable=self.hide).grid(row=2, column=0, columnspan=3, sticky="w")

        self.status = tk.StringVar(value="Idle. Open TradingView chart, then press START.  ESC = exit auto mode.")
        ttk.Label(root, textvariable=self.status, padding=(8, 4)).pack(fill="x")
        self.logbox = scrolledtext.ScrolledText(root, height=14, font=("Consolas", 9))
        self.logbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.log("Ready. Calibrate once before first run (Pine Editor positions).")
        root.after(100, self.poll)

    # ---------- logging / queue ----------
    def log(self, msg):
        self.q.put(("log", msg))

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.logbox.insert("end", val + "\n")
                    self.logbox.see("end")
                elif kind == "done":
                    self.btn_start.config(state="normal")
                    self.status.set("Idle.  ESC = exit auto mode.")
                    self.root.deiconify()
                elif kind == "key":
                    self.on_calib_key(val)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    # ---------- run ----------
    def options(self):
        return {"mode": self.mode.get(), "add_builtin": self.add_builtin.get(),
                "editor_open": self.editor_open.get(), "monitor": self.monitor.get(),
                "interval": self.interval.get()}

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.status.set("AUTO MODE RUNNING  -  press ESC to stop")
        if self.hide.get():
            self.root.iconify()
        engine = BotEngine(self.cfg, self.stop_event, self.hotkeys, self.log, self.options())

        def job():
            try:
                engine.run()
            finally:
                self.q.put(("done", None))

        self.worker = threading.Thread(target=job, daemon=True)
        self.worker.start()

    def test_analysis(self):
        def job():
            from bot.strategy import choose_strategy
            try:
                eng = BotEngine(self.cfg, self.stop_event, self.hotkeys, self.log, self.options())
                a = eng.analyze_once()
                self.log("Would use: " + choose_strategy(a, self.mode.get()).summary())
            except Exception as e:
                self.log(f"Analysis failed: {e}")
        threading.Thread(target=job, daemon=True).start()

    # ---------- calibration ----------
    def start_calibration(self):
        self.calib_index = 0
        self.log("--- Calibration started ---")
        self.prompt_calib()

    def prompt_calib(self):
        key, text = CALIB_STEPS[self.calib_index]
        self.status.set(f"Calibration {self.calib_index + 1}/{len(CALIB_STEPS)}: {text}")
        self.log(text)

    def on_calib_key(self, k):
        if self.calib_index is None:
            return
        name, _ = CALIB_STEPS[self.calib_index]
        if k == "f8":
            x, y = pyautogui.position()
            self.cfg["points"][name] = [int(x), int(y)]
            self.log(f"Saved {name} = ({x}, {y})")
        elif k == "f9":
            self.cfg["points"][name] = None
            self.log(f"Skipped {name}")
        self.calib_index += 1
        if self.calib_index >= len(CALIB_STEPS):
            self.calib_index = None
            self.cfg["monitor_interval_sec"] = int(self.interval.get())
            save_config(self.cfg)
            self.status.set("Calibration saved. Press START.")
            self.log("--- Calibration saved to config.json ---")
        else:
            self.prompt_calib()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
