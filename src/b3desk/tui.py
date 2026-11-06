"""Keyboard-first, local-only research desk."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Sparkline, Static, TabbedContent, TabPane

from b3desk.backtest import Result
from b3desk.presentation import discussion, overview
from b3desk.research import Snapshot, offline_debate


class Desk(App):
    TITLE = "B3 / RESEARCH DESK"
    SUB_TITLE = "Python calculates. Models narrate."
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("l", "language", "EN / PT"),
        ("s", "screenshot", "Save SVG"),
    ]
    CSS = """
    Screen { background: #0b1220; color: #e2e8f0; }
    Header { background: #172337; }
    Footer { background: #172337; }
    TabbedContent { height: 1fr; }
    #columns { height: auto; }
    #numbers { width: 45%; padding: 1 2; height: auto; }
    #committee { width: 55%; padding: 0 1; height: auto; }
    #equity { height: 5; margin: 0 2; color: #5eead4; }
    #warning { height: auto; padding: 1 2; color: #fbbf24; }
    #method { padding: 1 2; }
    DataTable { height: 1fr; }
    """

    def __init__(self, snapshot: Snapshot, result: Result):
        super().__init__()
        self.snapshot, self.result, self.lang = snapshot, result, "en"

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Desk", id="desk"):
                with VerticalScroll():
                    with Horizontal(id="columns"):
                        yield Static(overview(self.snapshot, self.result), id="numbers")
                        yield Static(discussion(offline_debate(self.snapshot)), id="committee")
                    yield Sparkline(self.result.equity, summary_function=max, id="equity")
                    yield Static(
                        "PAPER ONLY / Not investment advice. Offline commentary.\n"
                        "Não é recomendação de investimento.",
                        id="warning",
                    )
            with TabPane("Trade ledger", id="ledger"):
                yield DataTable(id="trades")
            with TabPane("Method", id="methodology"):
                yield Static(
                    "01  Signals use a trailing 31-session window.\n\n"
                    "02  Filings/news need availability strictly before signal day.\n\n"
                    f"03  Rebalance every {self.result.rebalance} session(s) at next open; "
                    f"max weight {self.result.max_weight:.0%}; integer shares, long-only.\n\n"
                    f"04  R${self.result.costs.brokerage:.2f}/order + "
                    f"{self.result.costs.exchange_bps:g} bps fees + "
                    f"{self.result.costs.slippage_bps:g} bps one-way slippage.\n\n"
                    "05  IBOV is a frictionless reference, not an executable portfolio.\n\n"
                    "06  Pre-tax; no dividend ledger, lending, interest or liquidation.\n\n"
                    "07  LLM text cannot place orders or change any calculation.\n\n"
                    + (
                        "Synthetic demo is a software test, not evidence of investment skill."
                        if self.snapshot.synthetic
                        else "Imported data: verify revisions and publication dates. Paper only."
                    ),
                    id="method",
                )
        yield Footer()

    def on_mount(self):
        table = self.query_one("#trades", DataTable)
        table.add_columns(
            "Fill date", "Signal date", "Side", "Shares", "Fill R$", "Fees R$", "Realized R$"
        )
        for trade in self.result.trades:
            table.add_row(
                trade.date,
                trade.signal_date,
                trade.side,
                str(trade.shares),
                f"{trade.price:.4f}",
                f"{trade.fees:.2f}",
                f"{trade.realized_pnl:.2f}",
            )

    def action_language(self):
        self.lang = "pt" if self.lang == "en" else "en"
        self.query_one("#committee", Static).update(
            discussion(offline_debate(self.snapshot, self.lang))
        )

    def action_screenshot(self):
        path = self.save_screenshot(path="output")
        self.notify(f"Saved {path}")
