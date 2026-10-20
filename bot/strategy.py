"""Chooses indicator + settings from the analysis and builds a Pine Script."""
from dataclasses import dataclass
from string import Template

TREND_PINE = Template(r'''//@version=5
indicator("AutoBot Trend Signals", shorttitle="AutoBot-T", overlay=true)
atrLen = input.int($atr_len, "ATR Length", minval=1)
factor = input.float($factor, "ATR Factor", step=0.1)
emaLen = input.int($ema_len, "EMA Filter Length", minval=1)
useEma = input.bool(true, "Use EMA Filter")

[st, dir] = ta.supertrend(factor, atrLen)
ema = ta.ema(close, emaLen)
flipUp = dir < 0 and dir[1] > 0
flipDn = dir > 0 and dir[1] < 0
buy  = flipUp and (not useEma or close > ema)
sell = flipDn and (not useEma or close < ema)

plot(dir < 0 ? st : na, "Trend Up", color=color.new(color.blue, 0), linewidth=2, style=plot.style_linebr)
plot(dir > 0 ? st : na, "Trend Down", color=color.new(color.orange, 0), linewidth=2, style=plot.style_linebr)
plot(ema, "EMA Filter", color=color.new(color.gray, 20))
plotshape(buy, title="BUY", style=shape.labelup, location=location.belowbar, color=color.new(color.lime, 0), text="BUY", textcolor=color.black, size=size.small)
plotshape(sell, title="SELL", style=shape.labeldown, location=location.abovebar, color=color.new(color.fuchsia, 0), text="SELL", textcolor=color.white, size=size.small)
alertcondition(buy, "AutoBot BUY", "AutoBot BUY on {{ticker}} @ {{close}}")
alertcondition(sell, "AutoBot SELL", "AutoBot SELL on {{ticker}} @ {{close}}")
''')

RANGE_PINE = Template(r'''//@version=5
indicator("AutoBot Range Signals", shorttitle="AutoBot-R", overlay=true)
rsiLen   = input.int($rsi_len, "RSI Length", minval=1)
osLvl    = input.int($os, "Oversold")
obLvl    = input.int($ob, "Overbought")
bbLen    = input.int($bb_len, "BB Length", minval=1)
bbMult   = input.float($bb_mult, "BB Multiplier", step=0.1)
lookback = input.int(3, "BB Touch Lookback", minval=1)

r = ta.rsi(close, rsiLen)
[basis, upper, lower] = ta.bb(close, bbLen, bbMult)
touchLow  = ta.lowest(low, lookback) <= lower
touchHigh = ta.highest(high, lookback) >= upper
buy  = ta.crossover(r, osLvl) and touchLow
sell = ta.crossunder(r, obLvl) and touchHigh

plot(basis, "BB Basis", color=color.new(color.gray, 30))
plot(upper, "BB Upper", color=color.new(color.blue, 30))
plot(lower, "BB Lower", color=color.new(color.blue, 30))
plotshape(buy, title="BUY", style=shape.labelup, location=location.belowbar, color=color.new(color.lime, 0), text="BUY", textcolor=color.black, size=size.small)
plotshape(sell, title="SELL", style=shape.labeldown, location=location.abovebar, color=color.new(color.fuchsia, 0), text="SELL", textcolor=color.white, size=size.small)
alertcondition(buy, "AutoBot BUY", "AutoBot BUY on {{ticker}} @ {{close}}")
alertcondition(sell, "AutoBot SELL", "AutoBot SELL on {{ticker}} @ {{close}}")
''')


@dataclass
class Strategy:
    kind: str        # "trend" | "range"
    builtin: str     # name typed into TradingView Indicators search
    params: dict
    pine: str

    def summary(self):
        return f"{self.kind.upper()} strategy | built-in: {self.builtin} | params: {self.params}"


def _clip(v, lo, hi):
    return max(lo, min(hi, v))


def choose_strategy(analysis, forced="auto"):
    kind = forced if forced in ("trend", "range") else ("range" if analysis.regime == "range" else "trend")
    vol = analysis.volatility
    if kind == "trend":
        params = {
            "atr_len": 10,
            "factor": round(_clip(2.0 + vol * 20, 2.0, 4.0), 1),
            "ema_len": 50 if analysis.efficiency > 0.5 else 100,
        }
        return Strategy("trend", "Supertrend", params, TREND_PINE.substitute(params))
    high_vol = vol > 0.05
    params = {
        "rsi_len": 14,
        "os": 25 if high_vol else 30,
        "ob": 75 if high_vol else 70,
        "bb_len": 20,
        "bb_mult": 2.5 if high_vol else 2.0,
    }
    return Strategy("range", "Bollinger Bands", params, RANGE_PINE.substitute(params))
