"""Screen-based chart analysis: reads candle pixels from the TradingView chart."""
from dataclasses import dataclass

import numpy as np


class AnalysisError(Exception):
    pass


@dataclass
class Analysis:
    regime: str          # "uptrend" | "downtrend" | "range"
    efficiency: float    # 0..1, how directional the move is
    r2: float            # linear-fit quality 0..1
    volatility: float    # avg candle span / chart height
    bullish_ratio: float # share of bullish candle pixels
    candles: int         # estimated candle count on screen

    def summary(self):
        return (f"regime={self.regime} | efficiency={self.efficiency:.2f} | R2={self.r2:.2f} | "
                f"volatility={self.volatility:.3f} | bullish={self.bullish_ratio:.0%} | candles~{self.candles}")


def grab_region(region):
    import mss
    with mss.mss() as sct:
        shot = sct.grab(region)
    arr = np.array(shot)            # BGRA
    return arr[:, :, :3][:, :, ::-1].copy()  # RGB


def _mask(img, rgb, tol):
    diff = np.abs(img.astype(np.int16) - np.array(rgb, dtype=np.int16))
    return diff.max(axis=2) <= tol


def analyze_image(img, up_rgb, down_rgb, tol=45):
    h, w = img.shape[:2]
    mu = _mask(img, up_rgb, tol)
    md = _mask(img, down_rgb, tol)
    m = mu | md
    # ignore columns with only a pixel or two (noise / anti-aliasing)
    col_count = m.sum(axis=0)
    cols = col_count >= 2
    xs = np.where(cols)[0]
    if len(xs) < 30:
        raise AnalysisError("Not enough candles detected. Check candle colors / zoom / chart visibility.")

    sub = m[:, xs]
    hi = sub.argmax(axis=0)                       # top pixel (high)
    lo = h - 1 - sub[::-1, :].argmax(axis=0)      # bottom pixel (low)
    mid = (hi + lo) / 2.0
    price = (h - mid) / h                         # 0..1, up = higher price
    span = (lo - hi) / h

    # candle count = number of contiguous column groups
    groups = int(np.sum(np.diff(np.concatenate(([0], cols.astype(np.int8)))) == 1))

    # down-sample to ~120 points
    n = min(120, len(price))
    chunks = np.array_split(price, n)
    p = np.array([c.mean() for c in chunks])
    p = p[-80:] if len(p) > 80 else p

    d = np.diff(p)
    efficiency = float(abs(p[-1] - p[0]) / (np.abs(d).sum() + 1e-9))
    t = np.arange(len(p))
    slope, intercept = np.polyfit(t, p, 1)
    fit = slope * t + intercept
    ss_res = float(((p - fit) ** 2).sum())
    ss_tot = float(((p - p.mean()) ** 2).sum()) + 1e-9
    r2 = max(0.0, 1 - ss_res / ss_tot)

    volatility = float(np.median(span))
    up_px, dn_px = int(mu.sum()), int(md.sum())
    bullish = up_px / max(1, up_px + dn_px)

    if efficiency > 0.30 and r2 > 0.40:
        regime = "uptrend" if slope > 0 else "downtrend"
    else:
        regime = "range"

    return Analysis(regime, efficiency, r2, volatility, bullish, groups)


def analyze_screen(region, cfg):
    img = grab_region(region)
    c = cfg["candle_colors"]
    return analyze_image(img, c["up"], c["down"], cfg["color_tolerance"])
