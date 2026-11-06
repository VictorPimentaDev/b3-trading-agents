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
    assert len(report["inputs"]["candles"]) == 220
    assert report["parameters"] == {"max_weight": 0.5, "rebalance": 5}
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


async def test_tui_method_reflects_parameters_and_source():
    from dataclasses import replace

    from textual.widgets import Static

    from b3desk.backtest import Costs

    data = replace(load(), synthetic=False)
    app = Desk(
        snapshot(data, 100, 0.2), run(data, costs=Costs(1, 2, 3), max_weight=0.2, rebalance=1)
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        method = str(app.query_one("#method", Static).content)
        assert "every 1 session" in method
        assert "max weight 20%" in method
        assert "R$1.00/order + 2 bps fees + 3 bps" in method
        assert "Imported data:" in method
        assert "Synthetic demo" not in method
