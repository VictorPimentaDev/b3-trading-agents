from dataclasses import replace

import pytest

from b3desk.data import Candle, Filing, load
from b3desk.research import allocation, snapshot


def test_filing_gate_uses_publication_not_period_end():
    data = load()
    before = next(i for i, c in enumerate(data.candles) if c.date == "2024-03-01")
    assert snapshot(data, before).margin is None
    assert snapshot(data, before + 1).margin == pytest.approx(0.15)


def test_round_trip(tmp_path):
    data = load()
    path = tmp_path / "data.json"
    data.save(path)
    assert load(path) == data


def test_bad_prices_and_order():
    with pytest.raises(ValueError):
        Candle("2024-01-01", 10, 8, 11, 9, 0, 100, 100)
    data = load()
    with pytest.raises(ValueError):
        replace(data, candles=tuple(reversed(data.candles)))
    with pytest.raises(ValueError):
        replace(data, candles=data.candles + (data.candles[-1],))
    with pytest.raises(ValueError):
        Filing("2024-12-31", "2024-01-01", 1, 1, 1, "source")


def test_risk_vetoes():
    assert allocation(-0.01, 0.1, 0.1, 0.5)[0] == 0
    assert allocation(0.1, 0.7, 0.1, 0.5)[0] == 0
    assert allocation(0.1, 0.1, -0.1, 0.5)[0] == 0
    assert allocation(0.1, 0.1, None, 0.5)[0] == 0.25
    assert allocation(0.1, 0.4, 0.1, 0.5)[0] == 0.25
    assert allocation(0.1, 0.1, 0.1, 0.1)[0] == 0.1


def test_noncanonical_date_cannot_bypass_point_in_time_gate():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        replace(load().filings[0], available_on="20240301")
