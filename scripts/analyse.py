#!/usr/bin/env python3
"""Read one token's candles and print a chart read for the chart-ideas skill.

    python3 analyse.py <address> <chainId> <timeframe>

Prints one JSON object: the last candles' facts, the indicators, the range
and swing points, and `drawings` / `markers` ready for the `price_chart` tool
(references/price-chart.md). It suggests; Butler decides the idea.

Candles come from GeckoTerminal's public API (the token's deepest pool), in
UTC, at candle-open times in unix seconds, the same grid the app's chart
uses. Standard library only: the butler's sandbox installs nothing.
"""
import json
import os
import sys
import urllib.request

API = "https://api.geckoterminal.com/api/v2"
NETWORKS = {
    1: "eth", 8453: "base", 56: "bsc", 42161: "arbitrum", 10: "optimism",
    137: "polygon_pos", 43114: "avax", 1399811149: "solana", 101: "solana",
}
# timeframe -> (GeckoTerminal unit, aggregate, how many of those make one candle)
FRAMES = {
    "1m": ("minute", 1, 1), "5m": ("minute", 5, 1), "30m": ("minute", 15, 2),
    "1h": ("hour", 1, 1), "4h": ("hour", 4, 1), "1d": ("day", 1, 1),
    "1w": ("day", 1, 7), "1mo": ("day", 1, 30),
}
SECONDS = {"1m": 60, "5m": 300, "30m": 1800, "1h": 3600, "4h": 14400,
           "1d": 86400, "1w": 604800, "1mo": 2592000}


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "butler-chart-ideas"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fail(msg):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def candles(address, chain_id, tf):
    net = NETWORKS.get(chain_id)
    if not net:
        fail(f"chain {chain_id} is not charted here; give the idea in words")
    pools = get(f"{API}/networks/{net}/tokens/{address}/pools?page=1").get("data") or []
    if not pools:
        fail("no pool for that token")
    # The deepest pool: the API's own order can lead with a new, thin one.
    top = max(pools, key=lambda p: float(p["attributes"].get("reserve_in_usd") or 0))
    pool = top["attributes"]["address"]
    base_is_token = (top.get("relationships", {}).get("base_token", {})
                     .get("data", {}).get("id", "").lower().endswith(address.lower()))
    unit, agg, group = FRAMES[tf]
    url = (f"{API}/networks/{net}/pools/{pool}/ohlcv/{unit}?aggregate={agg}&limit=1000"
           f"&currency=usd&token={'base' if base_is_token else 'quote'}")
    rows = get(url)["data"]["attributes"]["ohlcv_list"]
    rows = sorted(rows, key=lambda r: r[0])
    bars = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]),
             "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows]
    if group > 1:
        step = SECONDS[tf]
        out = {}
        for b in bars:
            t = b["time"] - b["time"] % step
            o = out.get(t)
            if o is None:
                out[t] = dict(b, time=t)
            else:
                o["high"] = max(o["high"], b["high"])
                o["low"] = min(o["low"], b["low"])
                o["close"] = b["close"]
                o["volume"] += b["volume"]
        bars = [out[k] for k in sorted(out)]
    return pool, bars


def ema(vals, n):
    k, out, e = 2 / (n + 1), [], None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(vals, n=14):
    if len(vals) <= n:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = vals[i] - vals[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def swings(bars, k=3):
    """Pivot highs and lows: a bar higher (lower) than the k bars each side."""
    hi, lo = [], []
    for i in range(k, len(bars) - k):
        win = bars[i - k:i + k + 1]
        if bars[i]["high"] == max(b["high"] for b in win):
            hi.append(bars[i])
        if bars[i]["low"] == min(b["low"] for b in win):
            lo.append(bars[i])
    return hi, lo


def main():
    if len(sys.argv) != 4 or sys.argv[3] not in FRAMES:
        fail("usage: analyse.py <address> <chainId> <1m|5m|30m|1h|4h|1d|1w|1mo>")
    address, chain_id, tf = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    try:
        pool, bars = candles(address, chain_id, tf)
    except Exception as e:  # network, 404, 429
        fail(f"could not read candles: {e}")
    if len(bars) < 30:
        fail(f"only {len(bars)} candles: too little history to read")

    # The candles as read, for render.py: the picture is drawn from the same
    # bars this read was made from.
    out_dir = os.path.join(os.environ.get("HOME") or ".", "charts")
    os.makedirs(out_dir, exist_ok=True)
    bars_file = os.path.join(out_dir, f"{address.lower()[:12]}-{chain_id}-{tf}.json")
    with open(bars_file, "w") as fh:
        json.dump(bars, fh)

    closes = [b["close"] for b in bars]
    e21, e55 = ema(closes, 21), ema(closes, 55)
    macd_line = [a - b for a, b in zip(ema(closes, 12), ema(closes, 26))]
    signal = ema(macd_line, 9)
    window = bars[-90:]
    floor = min(window, key=lambda b: b["low"])
    ceiling = max(window, key=lambda b: b["high"])
    sh, sl = swings(window)
    last = bars[-1]
    trend = ("up" if e21[-1] > e55[-1] and closes[-1] > e21[-1]
             else "down" if e21[-1] < e55[-1] and closes[-1] < e21[-1] else "sideways")

    drawings = [
        {"kind": "horizontal-ray", "points": [{"time": floor["time"], "price": floor["low"]}],
         "tone": "up", "text": "Support"},
        {"kind": "horizontal-ray", "points": [{"time": ceiling["time"], "price": ceiling["high"]}],
         "tone": "down", "text": "Resistance"},
    ]
    markers = []
    if len(sl) >= 2 and sl[-1]["low"] > sl[-2]["low"]:
        drawings.append({"kind": "trend-line", "tone": "accent", "points": [
            {"time": sl[-2]["time"], "price": sl[-2]["low"]},
            {"time": sl[-1]["time"], "price": sl[-1]["low"]}]})
        markers += [{"time": s["time"], "position": "below", "shape": "up",
                     "text": "Higher low", "tone": "up"} for s in sl[-2:]]
    if len(sh) >= 2 and sh[-1]["high"] < sh[-2]["high"]:
        drawings.append({"kind": "trend-line", "tone": "accent", "points": [
            {"time": sh[-2]["time"], "price": sh[-2]["high"]},
            {"time": sh[-1]["time"], "price": sh[-1]["high"]}]})
        markers += [{"time": s["time"], "position": "above", "shape": "down",
                     "text": "Lower high", "tone": "down"} for s in sh[-2:]]
    a, b = (floor, ceiling) if floor["time"] < ceiling["time"] else (ceiling, floor)
    drawings.append({"kind": "fib-retracement", "tone": "neutral", "points": [
        {"time": a["time"], "price": a["low"] if a is floor else a["high"]},
        {"time": b["time"], "price": b["low"] if b is floor else b["high"]}]})

    print(json.dumps({
        "pool": pool,
        "bars_file": bars_file,
        "timeframe": tf,
        "candles": len(bars),
        "last": last,
        "change_pct": round((closes[-1] / closes[-2] - 1) * 100, 2),
        "trend": trend,
        "ema21": e21[-1], "ema55": e55[-1],
        "rsi14": rsi(closes),
        "macd": macd_line[-1], "macd_signal": signal[-1],
        "range": {"floor": floor["low"], "floor_time": floor["time"],
                  "ceiling": ceiling["high"], "ceiling_time": ceiling["time"]},
        "swing_highs": [{"time": s["time"], "price": s["high"]} for s in sh[-4:]],
        "swing_lows": [{"time": s["time"], "price": s["low"]} for s in sl[-4:]],
        "drawings": drawings,
        "markers": markers,
    }))


if __name__ == "__main__":
    main()
