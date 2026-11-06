from dataclasses import asdict, replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from b3desk.backtest import Costs, Trade, run
from b3desk.data import load
from b3desk.taxes import estimate_simplified_ir


@pytest.fixture
def result():
    return run(load())


def sale(day, gross, pnl, fees=0):
    return Trade(day, "2023-01-01", "SELL", 1, gross, fees, pnl)


@pytest.mark.parametrize(
    "gross, expected", [(19999.99, "0.00"), (20000, "0.00"), (20000.01, "150.00")]
)
def test_exemption_uses_inclusive_gross_sales_limit(result, gross, expected):
    report = estimate_simplified_ir(
        replace(result, trades=(sale("2024-01-10", gross, 1000, fees=100),))
    )
    assert report.estimated_ir_brl == Decimal(expected)
    assert report.months[0].gross_sales_brl == Decimal(str(gross))


def test_monthly_netting_and_sales_aggregation(result):
    report = estimate_simplified_ir(
        replace(
            result,
            trades=(sale("2024-01-10", 12000, 2000), sale("2024-01-11", 9000, -500)),
        )
    )
    month = report.months[0]
    assert month.gross_sales_brl == 21000
    assert month.realized_pnl_brl == month.taxable_gain_brl == 1500
    assert month.estimated_ir_brl == Decimal("225.00")


def test_losses_cross_year_and_exempt_gains_preserve_them(result):
    trades = (
        sale("2023-12-10", 10000, -1000),  # Loss below the exemption threshold.
        sale("2024-01-10", 20000, 500),  # Exempt gain does not consume losses.
        sale("2024-03-10", 21000, 600),  # No sales in February.
        sale("2024-04-10", 21000, 1000),
        sale("2024-05-10", 21000, -2000),  # No refund of April's estimate.
    )
    report = estimate_simplified_ir(replace(result, trades=trades))
    assert [m.loss_carried_brl for m in report.months] == [1000, 1000, 400, 0, 2000]
    assert [m.taxable_gain_brl for m in report.months] == [0, 0, 0, 600, 0]
    assert report.estimated_ir_brl == Decimal("90.00")


def test_rounding_is_monthly_half_up(result):
    report = estimate_simplified_ir(
        replace(
            result,
            trades=(sale("2024-01-10", 11000, 0.05), sale("2024-01-11", 11000, 0.05)),
        )
    )
    assert report.estimated_ir_brl == Decimal("0.02")  # 0.10 × 15% = 0.015.


def test_no_sales_or_unrealized_gains_do_not_create_tax(result):
    buys = tuple(t for t in result.trades if t.side == "BUY")
    for trades in ((), buys):
        report = estimate_simplified_ir(replace(result, trades=trades))
        assert report.months == ()
        assert report.estimated_ir_brl == 0


def test_opt_in_preserves_entire_pre_tax_result_and_labels_partial_month(result):
    before, metrics = asdict(result), result.metrics
    report = estimate_simplified_ir(result)
    assert report == estimate_simplified_ir(result)
    assert asdict(result) == before
    assert result.metrics == metrics
    assert result == run(load())
    assert "SIMPLIFIED BR IR" in report.label
    assert "provisional" in report.label
    assert "not tax compliance" in report.label


def test_realized_pnl_includes_weighted_buy_basis_and_sell_costs_once(monkeypatch):
    data = load()
    prices = {31: 100, 32: 120, 33: 150}
    candles = tuple(
        replace(
            c,
            open=prices.get(i, 100),
            close=prices.get(i, 100),
            high=prices.get(i, 100),
            low=prices.get(i, 100),
        )
        for i, c in enumerate(data.candles[:34])
    )
    weights = {30: 0.25, 31: 0.5, 32: 0}
    monkeypatch.setattr(
        "b3desk.backtest.snapshot", lambda _, i, cap: SimpleNamespace(target_weight=weights[i])
    )
    result = run(replace(data, candles=candles), costs=Costs(2, 10, 20), rebalance=1)
    buy1, buy2, sell = result.trades
    assert (buy1.side, buy2.side, sell.side) == ("BUY", "BUY", "SELL")
    acquisition = sum(t.shares * t.price + t.fees for t in (buy1, buy2))
    expected_pnl = sell.shares * sell.price - sell.fees - acquisition
    assert sell.shares == buy1.shares + buy2.shares
    assert sell.realized_pnl == pytest.approx(expected_pnl)
    report = estimate_simplified_ir(result)
    assert report.months[0].realized_pnl_brl == Decimal(str(expected_pnl)).quantize(Decimal("0.01"))
    assert report.estimated_ir_brl == (
        report.months[0].realized_pnl_brl * Decimal("0.15")
    ).quantize(Decimal("0.01"))


@pytest.mark.parametrize(
    "change",
    [
        {"side": "SHORT"},
        {"shares": 0},
        {"shares": 1.5},
        {"price": float("nan")},
        {"price": 0},
        {"fees": -1},
        {"realized_pnl": float("inf")},
        {"date": "20240110"},
        {"side": "BUY", "realized_pnl": 10},
    ],
)
def test_invalid_fills_rejected(result, change):
    trade = replace(sale("2024-01-10", 21000, 1000), **change)
    with pytest.raises(ValueError):
        estimate_simplified_ir(replace(result, trades=(trade,)))


@pytest.mark.parametrize("day", ["2024-01-10", "2024-01-09"])
def test_same_day_and_out_of_order_fills_rejected(result, day):
    with pytest.raises(ValueError, match="ascending"):
        estimate_simplified_ir(
            replace(result, trades=(sale("2024-01-10", 21000, 100), sale(day, 21000, 100)))
        )
