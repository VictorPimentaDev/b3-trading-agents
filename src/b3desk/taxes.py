"""Opt-in Brazilian paper IR scenario; never an investor's tax calculation."""

import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from b3desk.backtest import Result
from b3desk.data import calendar_date


@dataclass(frozen=True)
class TaxMonth:
    month: str
    gross_sales_brl: Decimal
    realized_pnl_brl: Decimal
    exempt: bool
    taxable_gain_brl: Decimal
    estimated_ir_brl: Decimal
    loss_carried_brl: Decimal


@dataclass(frozen=True)
class SimplifiedIR:
    months: tuple[TaxMonth, ...]
    label: str = field(
        default="SIMPLIFIED BR IR — provisional paper estimate, single-stock resident PF scenario; "
        "rules reviewed 2026-11-06; not tax compliance or investment advice",
        init=False,
    )

    @property
    def estimated_ir_brl(self) -> Decimal:
        return sum((month.estimated_ir_brl for month in self.months), Decimal("0.00"))


def estimate_simplified_ir(result: Result) -> SimplifiedIR:
    """Summarize run() sales without changing fills, equity, cash or benchmark.

    Assumes only ordinary cash-equity trades, no other holdings or opening losses.
    All months are provisional: the input can end mid-month. See METHODOLOGY.md.
    """
    monthly: dict[str, tuple[Decimal, Decimal]] = {}
    previous = ""
    zero, cent = Decimal("0.00"), Decimal("0.01")
    for trade in result.trades:
        calendar_date(trade.date)
        if trade.date <= previous:
            raise ValueError("Expected ascending trades, at most one per day; no day trades")
        previous = trade.date
        if (
            trade.side not in ("BUY", "SELL")
            or type(trade.shares) is not int
            or trade.shares <= 0
            or any(not math.isfinite(v) for v in (trade.price, trade.fees, trade.realized_pnl))
            or trade.price <= 0
            or trade.fees < 0
            or (trade.side == "BUY" and trade.realized_pnl != 0)
        ):
            raise ValueError("Expected valid paper fills from backtest.run()")
        if trade.side == "SELL":
            month = trade.date[:7]
            sales, pnl = monthly.get(month, (zero, zero))
            monthly[month] = (
                sales + trade.shares * Decimal(str(trade.price)),
                pnl + Decimal(str(trade.realized_pnl)),
            )

    months = []
    loss = zero
    for month, (sales, pnl) in monthly.items():
        sales = sales.quantize(cent, rounding=ROUND_HALF_UP)
        pnl = pnl.quantize(cent, rounding=ROUND_HALF_UP)
        exempt = sales <= Decimal("20000.00")
        taxable = zero
        if pnl < 0:
            loss -= pnl
        elif not exempt:
            used = min(loss, pnl)
            loss -= used
            taxable = pnl - used
        tax = (taxable * Decimal("0.15")).quantize(cent, rounding=ROUND_HALF_UP)
        months.append(TaxMonth(month, sales, pnl, exempt, taxable, tax, loss))
    return SimplifiedIR(tuple(months))
