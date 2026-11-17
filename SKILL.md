---
name: chart-ideas
description: Chart a token on any timeframe as a picture with its key levels and trend lines drawn on it, post it, and say what it shows in a few lines.
version: 0.3.0
metadata: {"butler":{"moneyMoving":false,"keywords":["chart","chart this","ta","technical analysis","trade idea","setup","levels","support","resistance"],"requires":{"bins":["bevo-read","python3"]}}}
---

## When to use

Someone asks you to chart a token or read its chart: "chart virtual 1d", "VIRTUAL 4h
chart", "what does the AIXBT daily look like", "where are the levels on VIRTUAL". In a
group, the picture goes to the room with your answer.

A chart request is not a strategy request. Draw the chart. Only when they ask for a
setup, a trade idea or a strategy ("any setup on BRETT", "should I long here") do you
add a plan, and the plan goes in your words, never on the picture.

Not for: several tokens at once (chart the one they care about most and offer the
rest), tokenized stocks (use `token_card`), or placing a trade. If they then want to
act on the idea, that is a separate request through the normal trade flow.

## Before you start

Settle two things, from their words, without asking unless you truly cannot tell:

- **The token.** Resolve the ticker to one exact token:

  ```sh
  bevo-read token-search VIRTUAL
  ```

  Take the row they mean: the verified one, or the deepest liquidity when the rows
  are the same coin on several chains. When the rows are different coins with the same
  ticker, ask which one. Never chart a guess.

- **The indicators.** Only the ones they named: "with RSI" → `rsi`, "EMAs" → `ema`,
  "volume" → `volume`. None named, none drawn.

- **The timeframe.** One of `1m` `5m` `30m` `1h` `4h` `1d` `1w` `1mo`. Map what they
  said to the nearest: `15m` → `30m`, `2h` → `1h`, `12h` → `4h`, "daily" → `1d`,
  "weekly" → `1w`. No timeframe given: `4h` for "now / today / scalp", else `1d`.

What the picture can show, and the spec it takes, is in `references/chart-image.md`.
Read it before your first chart.

## Procedure

1. [FIXED] Read the candles and the indicators for that token and timeframe:

   ```sh
   python3 "$HOME/skills/chart-ideas/scripts/analyse.py" <address> <chainId> <timeframe>
   ```

   It prints JSON: `bars_file` (the candles it read), the last candle, trend, EMA 21/55,
   RSI 14, MACD, the range floor and ceiling, recent swing highs and lows, and suggested
   `drawings` and `markers`. An `error` key means no chart: go to Failure handling.

2. [ADAPT] Choose what to draw. For a chart request, the levels that matter: the
   support and resistance from step 1, and a trend line or the swing markers when the
   structure is clear. At most 4 drawings; no fib and no trade box unless asked.
   Only for a setup or strategy request, also decide a plan (long, short or no trade,
   with an entry, a stop and a target; at least 1.5 to 1, else say there is no trade)
   and add one position box:

   ```json
   {"kind": "long-position", "points": [{"time": <last candle time>, "price": <entry>}], "stop": <stop>, "target": <target>, "tone": "up"}
   ```

3. [ADAPT] Write the spec with your file tools to `$HOME/charts/spec.json`: `bars_file`
   from step 1, `symbol`, `timeframe`, `indicators` (only the ones asked for), and the
   `drawings` and `markers` from step 2. Every time must be a candle time from step 1's
   output. No title: the picture is the chart.

4. [FIXED] Draw the picture:

   ```sh
   python3 "$HOME/skills/chart-ideas/scripts/render.py" "$HOME/charts/spec.json" "$HOME/charts/chart.png"
   ```

5. [FIXED] Show it with the `share_image` tool, path `charts/chart.png`. In a group
   chat set `public: true`, or the room cannot see it; in your owner's private chat
   leave it off.

6. [ADAPT] Reply in a few short lines. For a chart request: what it shows (the trend,
   where it sits against its levels), two or three lines, no plan. For a setup or
   strategy request: the plan in words (entry, stop, target, risk to reward, what
   cancels it) and "Not financial advice." Do not list every figure on the picture.

## Idempotency and retries

Reading candles and drawing a picture change nothing, so a retry is safe. Post one
picture per request. If `render.py` fails, fix the spec it names and run it once more.
If `analyse.py` fails on the network, run it once more, then fall back to words.

## Failure handling

| Outcome | What to do |
| --- | --- |
| `analyse.py` prints `error` (no pool, unsupported chain, too few candles) | Say you could not chart it and why, in one line. Give whatever read you can from `token_card`. |
| `render.py` prints `error` or fails | Fix the spec once (a bad time, a missing price) and run it again; otherwise give the idea in words. |
| `share_image` answers `public: false` in a group | Say the room could not get the picture, and give the idea in words. |

## Limits

- One token and one timeframe per picture.
- On-chain tokens and native coins only; no stocks, no perps-only markets.
- The picture is the moment you drew it. It does not update; a chart that should keep
  watching is a duty, not this skill.
- You read price structure only: no news, no on-chain flows, unless you looked them up
  separately and say so.
- Never present an idea as certain, and never tell anyone to size a position.

## Say to the owner

For "chart virtual 1d":

> VIRTUAL on the daily: a run of lower highs since early October, now sitting just
> above its 0.418 support. Resistance is back at 0.886.

For "any setup on virtual?":

> On the daily it's at its 0.418 floor after a run of lower highs. A bounce long near
> 0.444 with a stop at 0.405 targets 0.528, about 2.1 to 1; a daily close under 0.418
> cancels it. Not financial advice.
