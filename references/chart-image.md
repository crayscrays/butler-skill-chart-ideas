# What `render.py` draws

`render.py` turns a spec into one PNG in the Virtuals app's dark chart style: the last
70 candles, the price now as an axis tag, and your drawings on top. Indicators appear
only when the spec names them. The picture has no title or idea line: what you think
of the chart goes in your reply. Other skills can use it to draw their own strategies.

```sh
python3 "$HOME/skills/chart-ideas/scripts/render.py" <spec.json> <out.png>
```

## The spec

```json
{
  "bars_file": "<bars_file from analyse.py>",
  "symbol": "VIRTUAL",
  "timeframe": "1d",
  "indicators": [],
  "drawings": [],
  "markers": [],
  "levels": []
}
```

| Field | Rule |
| --- | --- |
| `bars_file` | The path `analyse.py` printed. The picture is drawn from those exact candles. |
| `indicators` | Empty unless the person asked for them. `ema` (EMA 21 and 55 over the candles), `rsi` (an RSI 14 pane underneath), `volume` (faint bars along the bottom). |

Times are **unix seconds** of a candle's open, taken from `analyse.py`'s output. Prices
are plain USD numbers. The price axis widens to fit every price a drawing names, so a
far-away target still shows.

### `drawings[]`

Every drawing has a `kind`, `points` (`[{"time", "price"}]`), an optional `tone`
(`up` green, `down` red, `neutral` grey, `accent` blue) and an optional `text`.
There is no colour field: every chart wears the same palette.

| `kind` | Points | Drawn as |
| --- | --- | --- |
| `horizontal-ray` | 1 | A line from that candle to the right edge, its price tagged on the axis, `text` as its label |
| `horizontal-line` | 1 | The same across the whole chart |
| `trend-line` | 2 | A line between the two points |
| `ray` / `extended-line` | 2 | The same line run on to the right edge (`extended-line`: both edges) |
| `fib-retracement` | 2 | Levels 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1 from the first point's price to the second's, dashed, labelled |
| `rectangle` | 2 corners | A faint box in its tone, `text` top-left |
| `vertical-line` | 1 | A dashed line at that candle |
| `text` / `callout` / `note` | 1 | `text` at that point |
| `long-position` / `short-position` | 1 (entry) + `stop` + `target` prices | Green target zone, red stop zone, entry line with the risk to reward, both prices tagged; it reaches past the last candle |

An unknown `kind` is skipped.

### `markers[]`

```json
{ "time": 1793318400, "position": "below", "shape": "up", "text": "Higher low", "tone": "up" }
```

A small triangle above or below that candle, with up to 24 characters of text.

### `levels[]`

```json
{ "price": 0.85, "label": "Target", "tone": "up" }
```

A dashed line across the chart, labelled on the left and tagged on the axis.

## Keep it readable

At most about 6 drawings and 4 markers. Two lines at nearly the same price fight for
the same label space. Keep the one that says more.
