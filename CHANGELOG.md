# Changelog

## 0.3.0

- A chart request draws the chart: key levels only, no title or idea on the picture.
  A plan is added only when a setup is asked for, and it goes in the reply text.
- Indicators (`ema`, `rsi`, `volume`) are drawn only when asked for.

## 0.2.0

- Post the chart as a picture: `render.py` draws it in the app's dark chart style and
  Butler shares it with `share_image` (public in a group). The live `price_chart` card
  is gone.

## 0.1.0

- First version: chart one token on one timeframe with levels, trend lines, a fib and a
  long/short box, and explain the idea.
