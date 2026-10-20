"""Global keyboard listener: ESC = stop automation, F8/F9 = calibration."""
import time

from pynput import keyboard


class HotkeyListener:
    def __init__(self, on_esc):
        self.on_esc = on_esc
        self.on_other = None          # callback(key_name) used by calibration
        self._ignore_esc_until = 0.0
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True

    def start(self):
        self._listener.start()

    def ignore_esc(self, seconds=0.6):
        """Call before the bot itself presses ESC so it doesn't stop itself."""
        self._ignore_esc_until = time.time() + seconds

    def _on_press(self, key):
        try:
            if key == keyboard.Key.esc:
                if time.time() > self._ignore_esc_until:
                    self.on_esc()
            elif key in (keyboard.Key.f8, keyboard.Key.f9) and self.on_other:
                self.on_other("f8" if key == keyboard.Key.f8 else "f9")
        except Exception:
            pass
