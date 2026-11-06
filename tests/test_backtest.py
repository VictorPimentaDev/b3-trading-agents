import math
from dataclasses import replace

import pytest

from b3desk.backtest import Costs, run
from b3desk.data import load
from b3desk.research import snapshot


def test_demo_is_deterministic_and_all_trades_lag_signal():
    data = load()
    result = run(data)
    assert result == run(data)
    assert result.trades
    assert all(t.signal_date < t.date for t in result.trades)
    assert all(0 <= weight <= 1 for weight in result.exposure)
    assert result.metrics["fees_brl"] > 0
    assert result.metrics["slippage_brl"] > 0


def test_future_prices_filings_news_do_not_change_past():
    data = load()
    cut = 100
    changed = replace(
        data,
        candles=data.candles[:cut]
        + tuple(
            replace(c, open=c.open * 4, high=c.high * 4, low=c.low * 4, close=c.close * 4)
            for c in data.candles[cut:]
        ),
        filings=data.filings
        + (replace(data.filings[0], available_on=data.candles[cut].date, net_income=-1e9),),
    )
    old, new = run(data), run(changed)
    assert old.equity[: cut - 30] == new.equity[: cut - 30]
    assert snapshot(data, cut - 1) == snapshot(changed, cut - 1)


def test_flat_prices_lose_only_costs_and_no_fee_when_no_order():
    data = load()
    # A deterministic uptrend creates a buy; zero risk allocation creates no trades.
    result = run(data, max_weight=0)
    assert not result.trades
    assert set(result.equity) == {100_000}
    assert result.metrics["fees_brl"] == 0
    assert result.metrics["max_drawdown"] == 0


def test_exact_first_fill_and_accounting():
    data = load()
    candles = tuple(
        replace(
            c, open=100 + i, close=100 + i, high=100 + i, low=100 + i, ibov_open=200, ibov_close=200
        )
        for i, c in enumerate(data.candles[:32])
    )
    data = replace(data, candles=candles, filings=())
    result = run(data, cash=10_000, costs=Costs(2, 10, 20))
    fill = result.trades[0]
    expected_shares = math.floor(10_000 * 0.25 / 131)
    assert fill.shares == expected_shares
    assert fill.price == pytest.approx(131 * 1.002)
    assert fill.fees == pytest.approx(2 + fill.price * fill.shares * 0.001)
    cash = 10_000 - fill.shares * fill.price - fill.fees
    assert result.equity[-1] == pytest.approx(cash + fill.shares * 131)
    assert result.benchmark[-1] == 10_000


def test_fees_make_identical_fixed_schedule_worse():
    data = load()
    assert run(data, costs=Costs(0, 0, 0)).equity[-1] > run(data).equity[-1]


@pytest.mark.parametrize(
    "kwargs", [{"cash": 0}, {"cash": float("nan")}, {"rebalance": 0}, {"max_weight": 1.1}]
)
def test_invalid_backtest_parameters(kwargs):
    with pytest.raises(ValueError):
        run(load(), **kwargs)


@pytest.mark.parametrize(
    "kwargs", [{"brokerage": -1}, {"exchange_bps": float("nan")}, {"slippage_bps": 10_000}]
)
def test_invalid_costs(kwargs):
    with pytest.raises(ValueError):
        Costs(**kwargs)
