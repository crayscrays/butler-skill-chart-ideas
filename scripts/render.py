#!/usr/bin/env python3
"""Draw a token's chart as one picture, in the Virtuals app's dark chart style.

    python3 render.py <spec.json> <out.png>

`spec.json` (write it with your file tools):

    {
      "bars_file": "<the bars_file analyse.py printed>",
      "symbol": "VIRTUAL", "timeframe": "1d",
      "indicators": [],
      "drawings": [...], "markers": [...], "levels": [...]
    }

`drawings`, `markers` and `levels` are the shapes in references/chart-image.md;
anchor every point to a candle time from analyse.py. Prints the PNG path, then
show it with `share_image` (public: true in a group).

Needs Pillow (python3-pil) and a TrueType font, both in the butler image.
"""
import json
import math
import os
import sys
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

# The app's dark chart: AppColors.sheet ground, its border for the grid, and
# the market up/down pair; the indicator lines are the chart's own (i1/i3).
BG = (19, 19, 23)
GRID = (38, 38, 44)
TEXT = (154, 149, 140)
INK = (244, 241, 234)
UP = (79, 191, 135)
DOWN = (222, 106, 95)
ACCENT = (108, 166, 219)
EMA_FAST = (233, 185, 73)
EMA_SLOW = (194, 106, 207)
TONE = {"up": UP, "down": DOWN, "neutral": TEXT, "accent": ACCENT}
FIBS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]

W = 1000                   # the picture: read at phone width, so big type
H_PLAIN, H_RSI = 760, 900  # its height without and with the RSI pane
S = 2                      # drawn at twice the size, then smoothed down
BARS = 70                  # candles in view
BOX_BARS = 20              # empty candles right of the last, for a trade box

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def font(size, bold=False):
    for p in BOLD_PATHS if bold else FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size * S)
    return ImageFont.load_default()


def fail(msg):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def fmt(p):
    a = abs(p)
    if a >= 1000:
        return f"{p:,.0f}"
    if a >= 1:
        return f"{p:.2f}" if a >= 100 else f"{p:.3f}"
    if a == 0:
        return "0"
    dp = min(10, 3 - int(math.floor(math.log10(a))))
    return f"{p:.{dp}f}"


def ema(vals, n):
    k, out, e = 2 / (n + 1), [], None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def rsi_series(vals, n=14):
    out = [None] * len(vals)
    if len(vals) <= n:
        return out
    g = l = 0.0
    for i in range(1, n + 1):
        d = vals[i] - vals[i - 1]
        g += max(d, 0)
        l += max(-d, 0)
    ag, al = g / n, l / n
    out[n] = 100 - 100 / (1 + ag / al) if al else 100.0
    for i in range(n + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + ag / al) if al else 100.0
    return out


def main():
    if len(sys.argv) != 3:
        fail("usage: render.py <spec.json> <out.png>")
    spec = json.load(open(sys.argv[1]))
    all_bars = json.load(open(spec["bars_file"]))
    if len(all_bars) < 20:
        fail("too few candles to draw")
    closes_all = [b["close"] for b in all_bars]
    e_fast_all, e_slow_all = ema(closes_all, 21), ema(closes_all, 55)
    rsi_all = rsi_series(closes_all)
    start = max(0, len(all_bars) - BARS)
    bars = all_bars[start:]
    e_fast, e_slow, rsi = e_fast_all[start:], e_slow_all[start:], rsi_all[start:]
    times = [b["time"] for b in bars]
    step = times[-1] - times[-2] if len(times) > 1 else 86400
    drawings = spec.get("drawings") or []
    markers = spec.get("markers") or []
    levels = spec.get("levels") or []
    has_box = any(d.get("kind") in ("long-position", "short-position") for d in drawings)
    slots = len(bars) + (BOX_BARS if has_box else 3)

    # Only what was asked for: no indicator unless the request named it.
    ind = {str(i).lower() for i in (spec.get("indicators") or [])}
    show_ema, show_rsi, show_vol = "ema" in ind, "rsi" in ind, bool(ind & {"vol", "volume"})
    H = H_RSI if show_rsi else H_PLAIN
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    f_title, f_head, f_body, f_small = font(36, True), font(28, True), font(24), font(19)

    # ── Layout ────────────────────────────────────────────────────────────
    pad = 24
    axis_w = 118
    top = 92
    rsi_h = 120 if show_rsi else 0
    date_h = 34
    plot_l, plot_r = pad, W - pad - axis_w
    price_t, price_b = top, H - pad - rsi_h - date_h - (16 if show_rsi else 0)
    rsi_t, rsi_b = price_b + date_h + 30, H - pad

    def X(i):  # bar index (float) -> x
        return plot_l + (i + 0.5) * (plot_r - plot_l) / slots

    def index_of(t):
        if t <= times[0]:
            return (t - times[0]) / step
        if t >= times[-1]:
            return len(times) - 1 + (t - times[-1]) / step
        lo, hi = 0, len(times) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if times[mid] <= t:
                lo = mid
            else:
                hi = mid
        return lo + (t - times[lo]) / max(1, times[hi] - times[lo])

    # Price range: the candles, plus every price a drawing names.
    prices = [b["low"] for b in bars] + [b["high"] for b in bars]
    for dr in drawings:
        prices += [p["price"] for p in dr.get("points", []) if isinstance(p.get("price"), (int, float))]
        for k in ("stop", "target"):
            if isinstance(dr.get(k), (int, float)):
                prices.append(dr[k])
    prices += [l["price"] for l in levels if isinstance(l.get("price"), (int, float))]
    lo_p, hi_p = min(prices), max(prices)
    span = (hi_p - lo_p) or abs(hi_p) * 0.05 or 1
    lo_p, hi_p = lo_p - span * 0.06, hi_p + span * 0.06

    def Y(p):
        return price_b - (p - lo_p) / (hi_p - lo_p) * (price_b - price_t)

    def line(pts, color, width=2, dash=None):
        pts = [(x * S, y * S) for x, y in pts]
        if not dash:
            d.line(pts, fill=color, width=width * S, joint="curve")
            return
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        length = math.hypot(x1 - x0, y1 - y0)
        if length == 0:
            return
        on, off = dash[0] * S, dash[1] * S
        pos = 0
        while pos < length:
            a, b = pos / length, min(pos + on, length) / length
            d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a),
                    (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=color, width=width * S)
            pos += on + off

    def text(x, y, s, color, f, anchor="la"):
        d.text((x * S, y * S), s, fill=color, font=f, anchor=anchor)

    def rect(x0, y0, x1, y1, fill=None, outline=None, radius=0):
        box = [min(x0, x1) * S, min(y0, y1) * S, max(x0, x1) * S, max(y0, y1) * S]
        if radius:
            d.rounded_rectangle(box, radius=radius * S, fill=fill, outline=outline)
        else:
            d.rectangle(box, fill=fill, outline=outline)

    placed = []

    def tag(y, label, color, ink=BG):
        """A price pill on the axis, the chart's own, nudged off any other."""
        for _ in range(8):
            hit = next((q for q in placed if abs(q - y) < 30), None)
            if hit is None:
                break
            y = hit + 30 if y >= hit else hit - 30
        placed.append(y)
        w = d.textlength(label, font=f_small) / S + 14
        rect(plot_r + 6, y - 14, plot_r + 6 + w, y + 14, fill=color, radius=5)
        text(plot_r + 13, y, label, ink, f_small, "lm")

    def blend(c, a):
        return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))

    # ── Header ────────────────────────────────────────────────────────────
    last, prev = bars[-1], bars[-2]
    chg = (last["close"] / prev["close"] - 1) * 100 if prev["close"] else 0
    sym = f"{spec.get('symbol', '?')}/USD · {spec.get('timeframe', '').upper()}"
    text(pad, 20, sym, INK, f_title)
    x_after = pad + d.textlength(sym, font=f_title) / S + 18
    text(x_after, 30, fmt(last["close"]), INK, f_head)
    x_after += d.textlength(fmt(last["close"]), font=f_head) / S + 10
    text(x_after, 31, f"{chg:+.2f}%", UP if chg >= 0 else DOWN, f_body)
    stamp = datetime.fromtimestamp(times[-1], timezone.utc).strftime("%b %d, %Y")
    text(W - pad, 30, f"Butler · {stamp}", TEXT, f_small, "ra")

    # ── Grid and axes ─────────────────────────────────────────────────────
    nice = 10 ** math.floor(math.log10((hi_p - lo_p) / 5))
    for m in (1, 2, 2.5, 5, 10):
        if (hi_p - lo_p) / (nice * m) <= 6:
            nice *= m
            break
    tagged = [bars[-1]["close"]] + [l["price"] for l in levels if isinstance(l.get("price"), (int, float))]
    for dr in drawings:
        if dr.get("kind") in ("horizontal-line", "horizontal-ray"):
            tagged += [q["price"] for q in (dr.get("points") or [])[:1]]
        tagged += [dr[k] for k in ("stop", "target") if isinstance(dr.get(k), (int, float))]
    p = math.ceil(lo_p / nice) * nice
    while p <= hi_p:
        y = Y(p)
        line([(plot_l, y), (plot_r, y)], GRID, 1)
        # A tag at this height already names a price; the grid's label hides.
        if not any(abs(Y(q) - y) < 26 for q in tagged):
            text(plot_r + 12, y, fmt(p), TEXT, f_small, "lm")
        p += nice
    for k in range(0, len(bars), max(1, len(bars) // 5)):
        x = X(k)
        line([(x, price_t), (x, price_b)], GRID, 1)
        if show_rsi:
            line([(x, rsi_t), (x, rsi_b)], GRID, 1)
        label = datetime.fromtimestamp(times[k], timezone.utc).strftime(
            "%b %d" if step >= 3600 * 4 else "%H:%M")
        text(max(x, plot_l + d.textlength(label, font=f_small) / S / 2), price_b + 10, label, TEXT, f_small, "ma")

    # ── Candles and EMAs ──────────────────────────────────────────────────
    bw = max(1.0, (plot_r - plot_l) / slots * 0.62)
    # Volume sits under the candles, faint, along the bottom of the pane.
    if show_vol:
        vmax = max((b.get("volume") or 0) for b in bars) or 1
        vh = (price_b - price_t) * 0.18
        for i, b in enumerate(bars):
            c = blend(UP if b["close"] >= b["open"] else DOWN, 0.35)
            x = X(i)
            rect(x - bw / 2, price_b - (b.get("volume") or 0) / vmax * vh, x + bw / 2, price_b, fill=c)
    for i, b in enumerate(bars):
        c = UP if b["close"] >= b["open"] else DOWN
        x = X(i)
        line([(x, Y(b["high"])), (x, Y(b["low"]))], c, 1)
        y0, y1 = Y(b["open"]), Y(b["close"])
        if abs(y1 - y0) < 1:
            y1 = y0 + 1
        rect(x - bw / 2, y0, x + bw / 2, y1, fill=c)
    for series, col in ((e_fast, EMA_FAST), (e_slow, EMA_SLOW)) if show_ema else ():
        line([(X(i), Y(v)) for i, v in enumerate(series)], col, 2)
    if show_ema:
        text(plot_l + 6, price_t + 4, "EMA21", EMA_FAST, f_small)
        text(plot_l + 86, price_t + 4, "EMA55", EMA_SLOW, f_small)

    # ── Butler's drawings ─────────────────────────────────────────────────
    right_x = plot_r
    # Trade boxes first, so every line and label lands on top of their fill.
    drawings = sorted(drawings, key=lambda dr: dr.get("kind") not in ("long-position", "short-position"))
    flat = [p["price"] for dr in drawings if dr.get("kind") in ("horizontal-line", "horizontal-ray")
            for p in (dr.get("points") or [])[:1]]
    # A trade box labels its own target and stop.
    flat += [dr[k] for dr in drawings if dr.get("kind") in ("long-position", "short-position")
             for k in ("stop", "target") if isinstance(dr.get(k), (int, float))]
    for dr in drawings:
        kind, pts = dr.get("kind"), dr.get("points") or []
        col = TONE.get(dr.get("tone"), TEXT)
        label = (dr.get("text") or "")[:40]
        if not pts:
            continue
        x0, y0 = X(index_of(pts[0]["time"])), Y(pts[0]["price"])
        if kind in ("horizontal-line", "horizontal-ray"):
            line([(plot_l if kind == "horizontal-line" else x0, y0), (right_x, y0)], col, 2)
            if label:
                # Under a line below the price, over one above it: the side
                # away from the candles it was drawn against.
                below = pts[0]["price"] < bars[-1]["close"]
                text(right_x - 8, y0 + 6 if below else y0 - 6, label, col, f_small, "rt" if below else "rb")
            tag(y0, fmt(pts[0]["price"]), col)
        elif kind in ("trend-line", "ray", "extended-line") and len(pts) >= 2:
            x1, y1 = X(index_of(pts[1]["time"])), Y(pts[1]["price"])
            if kind != "trend-line" and x1 != x0:
                k = (y1 - y0) / (x1 - x0)
                if kind == "extended-line":
                    x0, y0 = plot_l, y0 + k * (plot_l - x0)
                x1, y1 = right_x, y1 + k * (right_x - x1)
            line([(x0, y0), (x1, y1)], col, 2)
            if label:
                text((x0 + x1) / 2, (y0 + y1) / 2 - 8, label, col, f_small, "mb")
        elif kind == "fib-retracement" and len(pts) >= 2:
            pa, pb = pts[0]["price"], pts[1]["price"]
            xa = min(x0, X(index_of(pts[1]["time"])))
            for lv in FIBS:
                p = pb + (pa - pb) * lv
                y = Y(p)
                line([(xa, y), (right_x, y)], blend(col, 0.75), 1, dash=(6, 5))
                # A drawn line at this price already says it.
                if not any(abs(Y(q) - y) < 14 for q in flat):
                    text(right_x - 6, y - 4, f"{lv:g}  {fmt(p)}", blend(col, 0.9), f_small, "rb")
        elif kind == "rectangle" and len(pts) >= 2:
            x1, y1 = X(index_of(pts[1]["time"])), Y(pts[1]["price"])
            rect(x0, y0, x1, y1, fill=blend(col, 0.16))
            line([(x0, y0), (x1, y0)], col, 1)
            line([(x0, y1), (x1, y1)], col, 1)
            if label:
                text(min(x0, x1) + 6, min(y0, y1) + 4, label, col, f_small)
        elif kind == "vertical-line":
            line([(x0, price_t), (x0, price_b)], col, 1, dash=(6, 5))
        elif kind in ("text", "callout", "note"):
            text(x0, y0, label, col, f_body, "mm")
        elif kind in ("long-position", "short-position"):
            entry = pts[0]["price"]
            stop, target = dr.get("stop"), dr.get("target")
            if not isinstance(stop, (int, float)) or not isinstance(target, (int, float)):
                continue
            xe = X(index_of(pts[0]["time"]))
            xr = X(len(bars) - 1 + BOX_BARS - 1)
            ye, ys, yt = Y(entry), Y(stop), Y(target)
            rect(xe, ye, xr, yt, fill=blend(UP, 0.22))
            rect(xe, ye, xr, ys, fill=blend(DOWN, 0.22))
            line([(xe, ye), (xr, ye)], INK, 2)
            risk = abs(entry - stop)
            rr = abs(target - entry) / risk if risk else 0
            t_pct = (target / entry - 1) * 100 if entry else 0
            s_pct = (stop / entry - 1) * 100 if entry else 0
            # Outside the box, past its far edge, so no line inside it can
            # run through the words.
            text(xe + 4, yt - 6 if yt < ye else yt + 6, f"Target {fmt(target)} ({t_pct:+.1f}%)",
                 UP, f_small, "ld" if yt < ye else "la")
            text(xe + 4, ys + 6 if ys > ye else ys - 6, f"Stop {fmt(stop)} ({s_pct:+.1f}%)",
                 DOWN, f_small, "la" if ys > ye else "ld")
            text(xe + 8, ye - 6, f"Entry {fmt(entry)} · {rr:.1f}R", INK, f_small, "ld")
            tag(yt, fmt(target), UP)
            tag(ys, fmt(stop), DOWN)
    for lv in levels:
        col = TONE.get(lv.get("tone"), TEXT)
        y = Y(lv["price"])
        line([(plot_l, y), (right_x, y)], col, 1, dash=(8, 6))
        if lv.get("label"):
            text(plot_l + 6, y - 4, lv["label"][:24], col, f_small, "lb")
        tag(y, fmt(lv["price"]), col)

    # ── Markers ───────────────────────────────────────────────────────────
    by_time = {b["time"]: b for b in bars}
    for m in markers:
        b = by_time.get(m.get("time"))
        if not b:
            continue
        col = TONE.get(m.get("tone"), TEXT)
        x = X(index_of(b["time"]))
        above = m.get("position") == "above"
        y = Y(b["high"]) - 10 if above else Y(b["low"]) + 10
        sz = 8
        if m.get("shape") == "down" or (above and m.get("shape") != "up"):
            tri = [(x - sz, y - sz), (x + sz, y - sz), (x, y)]
        else:
            tri = [(x - sz, y + sz), (x + sz, y + sz), (x, y)]
        d.polygon([(px * S, py * S) for px, py in tri], fill=col)
        if m.get("text"):
            text(x, y - sz - 6 if above else y + sz + 6, m["text"][:24], col, f_small,
                 "md" if above else "ma")

    # The price now, the chart's own tag.
    last_col = UP if last["close"] >= last["open"] else DOWN
    line([(plot_l, Y(last["close"])), (plot_r, Y(last["close"]))], blend(last_col, 0.7), 1, dash=(3, 4))
    tag(Y(last["close"]), fmt(last["close"]), last_col)

    # ── RSI ───────────────────────────────────────────────────────────────
    out = None if show_rsi else img.resize((W, H), Image.LANCZOS)

    def RY(v):
        return rsi_b - v / 100 * (rsi_b - rsi_t)

    for lv in (30, 70) if show_rsi else ():
        line([(plot_l, RY(lv)), (plot_r, RY(lv))], GRID, 1, dash=(6, 5))
        text(plot_r + 12, RY(lv), str(lv), TEXT, f_small, "lm")
    if show_rsi:
        pts = [(X(i), RY(v)) for i, v in enumerate(rsi) if v is not None]
        if len(pts) > 1:
            line(pts, EMA_FAST, 2)
        now_rsi = next((v for v in reversed(rsi) if v is not None), None)
        text(pad, rsi_t - 4, f"RSI14 {now_rsi:.1f}" if now_rsi is not None else "RSI14", EMA_FAST, f_small, "ld")
        out = img.resize((W, H), Image.LANCZOS)
    out.save(sys.argv[2], "PNG", optimize=True)
    print(sys.argv[2])


if __name__ == "__main__":
    main()
