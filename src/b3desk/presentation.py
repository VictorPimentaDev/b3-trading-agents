"""Rich views shared by the command line and Textual desk."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from b3desk.backtest import Result
from b3desk.research import Snapshot


def overview(s: Snapshot, result: Result):
    metrics = result.metrics
    table = Table(expand=True, border_style="#334155", padding=(0, 2))
    table.add_column("RESEARCH / " + s.ticker, style="bold #5eead4")
    table.add_column("VALUE", justify="right")
    for label, value in (
        ("As of", s.as_of),
        ("20-session momentum", f"{s.momentum:+.2%}"),
        ("Annualized volatility", f"{s.volatility:.2%}"),
        ("Next-open target", f"{s.target_weight:.0%}"),
        ("Paper return · after costs, pre-tax", f"{metrics['return']:+.2%}"),
        ("IBOV reference · gross", f"{metrics['ibov_return']:+.2%}"),
        ("Max drawdown", f"{metrics['max_drawdown']:.2%}"),
        ("Fees / slippage", f"R$ {metrics['fees_brl']:.2f} / R$ {metrics['slippage_brl']:.2f}"),
        ("Trades", str(metrics["trades"])),
    ):
        table.add_row(label, value)
    label = (
        "SYNTHETIC DEMO · NOT HISTORICAL PERFORMANCE"
        if s.synthetic
        else "IMPORTED DATA · PAPER ONLY"
    )
    return Group(Text(label, style="bold yellow"), table, Text(s.reason, style="dim"))


def discussion(transcript: dict[str, str]):
    table = Table(expand=True, show_header=False, box=None, padding=(1, 1))
    table.add_column(style="bold #5eead4", width=13)
    table.add_column()
    for role, message in transcript.items():
        table.add_row(role.upper(), Text(message))
    return Panel(table, title="RESEARCH COMMITTEE / NARRATION", border_style="#334155")
