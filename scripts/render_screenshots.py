"""Run with `uv run --with resvg-py python scripts/render_screenshots.py`."""

from pathlib import Path

import resvg_py
from PIL import Image, ImageDraw, ImageFont

for name in ("desk", "ledger"):
    Path(f"docs/{name}.png").write_bytes(
        resvg_py.svg_to_bytes(
            svg_path=f"docs/{name}.svg", width=1500, font_family="Menlo", monospace_family="Menlo"
        )
    )

cover = Image.new("RGB", (1280, 640), "#0b1220")
draw = ImageDraw.Draw(cover)
font = ImageFont.load_default(size=42)
small = ImageFont.load_default(size=22)
draw.text((64, 52), "B3 / TRADING AGENTS", font=font, fill="#5eead4")
draw.text((64, 114), "Python calculates. Models narrate.", font=small, fill="#e2e8f0")
chart = Image.open("docs/equity.png")
chart.thumbnail((730, 390))
cover.paste(chart, (500, 205))
for i, text in enumerate(
    (
        "CVM fundamentals",
        "Bull / bear debate",
        "Paper ledger + costs",
        "OpenAI / Anthropic / Ollama",
    )
):
    draw.text((64, 230 + i * 55), text, font=small, fill="#cbd5e1")
draw.text(
    (64, 575), "RESEARCH ONLY / SYNTHETIC DEMO / NOT INVESTMENT ADVICE", font=small, fill="#fbbf24"
)
cover.save("docs/social-preview.png")
assert Image.open("docs/social-preview.png").size == (1280, 640)
assert all(Image.open(f"docs/{name}.png").width == 1500 for name in ("desk", "ledger"))
