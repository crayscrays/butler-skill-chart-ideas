# butler-skill-chart-ideas

A Butler hub skill: "@butler chart virtual 1d" draws a chart picture of the token with
Butler's levels, trend lines and a trade idea on it, posts it, and explains the idea.

- `SKILL.md` — the playbook Butler follows.
- `scripts/analyse.py` — reads candles from GeckoTerminal and prints indicators, the
  range, swing points and suggested drawings. Standard library only.
- `scripts/render.py` — draws the picture from those candles and a spec of drawings.
- `references/chart-image.md` — the spec: what can be drawn. Other skills can use the
  same renderer to draw their own strategies.

Needs `python3-pil` and `fonts-dejavu-core` in the Butler image, and `share_image`'s
`public` option so a group can see the picture.

Validate before a release:

```bash
curl -sSLO https://virtual-protocol.github.io/butler-skills/tools/validate.py
python3 validate.py --standalone .
```
