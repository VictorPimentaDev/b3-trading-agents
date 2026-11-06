"""Capture the actual Textual UI without opening a persistent terminal."""

import asyncio
import os
from pathlib import Path

from b3desk.backtest import run
from b3desk.data import load
from b3desk.research import snapshot
from b3desk.tui import Desk


async def main():
    os.environ.pop("NO_COLOR", None)
    data = load()
    app = Desk(snapshot(data, len(data.candles) - 1), run(data))
    async with app.run_test(size=(150, 44)) as pilot:
        await pilot.pause()
        Path("docs").mkdir(exist_ok=True)
        app.save_screenshot("desk.svg", "docs")
        await pilot.click("#--content-tab-ledger")
        await pilot.pause()
        app.save_screenshot("ledger.svg", "docs")
        for path in Path("docs").glob("*.svg"):
            path.write_text(
                "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
            )


if __name__ == "__main__":
    asyncio.run(main())
