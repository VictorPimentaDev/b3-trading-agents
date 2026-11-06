# Reproduce the visuals

```sh
uv run b3desk demo
cp output/equity.png docs/equity.png
uv run python scripts/capture_desk.py
uv run --with resvg-py python scripts/render_screenshots.py
```

`capture_desk.py` runs the actual Textual app in its headless test driver, changes the active tab and
exports two SVG screenshots. It removes `NO_COLOR` only for this documentation capture. The application
itself respects the terminal's color preference. `resvg-py` is a temporary documentation tool, not a
runtime dependency. Local fonts can alter glyph appearance; captures here use Menlo.

`social-preview.png` is a 1280 × 640 cover generated from the same chart and labels. Upload it through
GitHub repository Settings → General → Social preview when preparing the public launch; merely
committing an image does not configure GitHub's social preview. No production screenshots or customer
data are used.
