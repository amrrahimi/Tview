"""Main bot loop: analyze -> pick indicator -> configure -> show signals -> monitor."""
import pyautogui

from .analyzer import AnalysisError, analyze_screen
from .automation import ConfigError, Controller, StopRequested
from .strategy import choose_strategy


class BotEngine:
    def __init__(self, cfg, stop_event, hotkeys, log, options):
        self.cfg = cfg
        self.stop_event = stop_event
        self.log = log
        self.opt = options
        self.ctl = Controller(cfg, stop_event, hotkeys, log)

    def analyze_once(self):
        self.ctl.find_window()
        self.ctl.activate()
        a = analyze_screen(self.ctl.chart_region(), self.cfg)
        self.log("Analysis: " + a.summary())
        return a

    def run(self):
        try:
            self.log("=== Auto mode ON (press ESC to exit) ===")
            a = self.analyze_once()
            strat = choose_strategy(a, self.opt["mode"])
            self.log("Selected: " + strat.summary())

            if self.opt["add_builtin"]:
                self.ctl.add_builtin_indicator(strat.builtin)
            self.ctl.apply_pine(strat.pine, self.opt["editor_open"])
            editor_open = True

            if not self.opt["monitor"]:
                self.log("Done.")
                return
            interval = max(10, int(self.opt["interval"]))
            current = strat.kind
            self.log(f"Monitoring chart every {interval}s ...")
            while True:
                self.ctl.wait(interval)
                try:
                    a = analyze_screen(self.ctl.chart_region(), self.cfg)
                except AnalysisError as e:
                    self.log(f"Skip: {e}")
                    continue
                new = choose_strategy(a, self.opt["mode"])
                self.log("Re-check: " + a.summary())
                if new.kind != current:
                    self.log(f"Market regime changed -> switching to {new.kind.upper()}")
                    self.ctl.activate()
                    self.ctl.apply_pine(new.pine, editor_open)
                    current = new.kind
        except StopRequested:
            self.log("ESC pressed: auto mode OFF.")
        except pyautogui.FailSafeException:
            self.log("Fail-safe (mouse in screen corner): auto mode OFF.")
        except (ConfigError, AnalysisError) as e:
            self.log(f"Error: {e}")
        except Exception as e:
            self.log(f"Unexpected error: {e!r}")
