import json

from b3desk.backtest import run
from b3desk.cli import main
from b3desk.data import load
from b3desk.research import snapshot
from b3desk.tui import Desk


def test_cli_produces_chart_and_auditable_report(tmp_path):
    assert main(["demo", "--out", str(tmp_path)]) == 0
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["snapshot"]["synthetic"] is True
    assert report["narration_provider"] == "offline"
    assert (tmp_path / "equity.png").read_bytes().startswith(b"\x89PNG")
    assert main(["demo", "--cash", "-1"]) == 2


async def test_tui_keyboard_and_ledger():
    from textual.widgets import DataTable

    data = load()
    app = Desk(snapshot(data, len(data.candles) - 1), run(data))
    async with app.run_test(size=(140, 45)) as pilot:
        assert app.query_one("#trades", DataTable).row_count == len(app.result.trades)
        await pilot.press("l")
        assert app.lang == "pt"
        await pilot.click("#--content-tab-ledger")
        await pilot.pause()
        assert app.query_one("#trades", DataTable).display
