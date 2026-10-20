"""Mouse/keyboard control of the TradingView window."""
import time

import pyautogui
import pyperclip

pyautogui.FAILSAFE = True   # slam mouse into a screen corner = emergency stop
pyautogui.PAUSE = 0.05


class StopRequested(Exception):
    pass


class ConfigError(Exception):
    pass


class Controller:
    def __init__(self, cfg, stop_event, hotkeys, log):
        self.cfg = cfg
        self.stop_event = stop_event
        self.hotkeys = hotkeys
        self.log = log
        self.win = None

    # ---------- helpers ----------
    def check(self):
        if self.stop_event.is_set():
            raise StopRequested()

    def wait(self, key_or_sec):
        sec = self.cfg["delays"].get(key_or_sec, 1.0) if isinstance(key_or_sec, str) else key_or_sec
        end = time.time() + sec
        while time.time() < end:
            self.check()
            time.sleep(0.05)

    def press_esc(self):
        self.hotkeys.ignore_esc(0.6)
        pyautogui.press("esc")

    def click(self, point):
        self.check()
        pyautogui.moveTo(point[0], point[1], duration=0.25)
        pyautogui.click()

    # ---------- window ----------
    def find_window(self):
        import pygetwindow as gw
        kw = self.cfg["window_title_keyword"].lower()
        wins = [w for w in gw.getAllWindows() if kw in (w.title or "").lower() and w.width > 300 and w.height > 300]
        if not wins:
            raise ConfigError("TradingView window not found. Open tradingview.com chart in your browser first.")
        self.win = wins[0]
        return self.win

    def activate(self):
        w = self.win
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
        except Exception:
            pass  # pygetwindow often raises a harmless "operation completed successfully"
        self.wait("medium")

    def chart_region(self):
        w = self.win
        m = self.cfg["chart_margins"]
        left = int(w.left + w.width * m["left"])
        top = int(w.top + w.height * m["top"])
        width = int(w.width * (1 - m["left"] - m["right"]))
        height = int(w.height * (1 - m["top"] - m["bottom"]))
        return {"left": max(0, left), "top": max(0, top), "width": width, "height": height}

    def focus_chart(self):
        r = self.chart_region()
        self.click((r["left"] + r["width"] // 2, r["top"] + r["height"] // 2))
        self.wait("short")

    # ---------- actions ----------
    def add_builtin_indicator(self, name):
        self.log(f"Opening Indicators and searching '{name}' ...")
        self.focus_chart()
        pyautogui.press("/")             # TradingView shortcut: Indicators dialog
        self.wait("medium")
        self.check()
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(name, interval=0.04)
        self.wait("long")
        self.check()
        pyautogui.press("enter")         # add first result
        self.wait("medium")
        self.press_esc()                 # close dialog
        self.wait("short")
        self.log(f"Built-in '{name}' added.")

    def apply_pine(self, code, editor_already_open=False):
        pts = self.cfg["points"]
        if not pts.get("pine_editor_text") or (not editor_already_open and not pts.get("pine_editor_tab")):
            raise ConfigError("Pine Editor positions not calibrated. Press 'Calibrate' first.")
        self.log("Writing signal script into Pine Editor ...")
        pyperclip.copy(code)
        if not editor_already_open:
            self.click(pts["pine_editor_tab"])
            self.wait("long")
        self.click(pts["pine_editor_text"])
        self.wait("short")
        pyautogui.hotkey("ctrl", "a")
        self.wait(0.2)
        pyautogui.hotkey("ctrl", "v")
        self.wait("medium")
        self.check()
        if pts.get("add_to_chart_button"):
            self.click(pts["add_to_chart_button"])
        else:
            pyautogui.hotkey(*self.cfg["add_to_chart_hotkey"])
        self.wait("long")
        self.log("Script added to chart: BUY / SELL labels should now be visible.")
