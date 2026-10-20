import copy
import json
import os
import sys

DEFAULTS = {
    "window_title_keyword": "TradingView",
    # Screen points recorded with the Calibrate wizard (x, y) or null
    "points": {
        "pine_editor_tab": None,
        "pine_editor_text": None,
        "add_to_chart_button": None,
    },
    # TradingView default candle colors (RGB)
    "candle_colors": {"up": [8, 153, 129], "down": [242, 54, 69]},
    "color_tolerance": 45,
    # Part of the window cropped away before analysis (fractions)
    "chart_margins": {"left": 0.05, "top": 0.14, "right": 0.09, "bottom": 0.18},
    "delays": {"short": 0.4, "medium": 1.0, "long": 2.5},
    "add_to_chart_hotkey": ["ctrl", "enter"],
    "monitor_interval_sec": 60,
}


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


CONFIG_PATH = os.path.join(app_dir(), "config.json")


def _merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config():
    cfg = copy.deepcopy(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _merge(cfg, json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
