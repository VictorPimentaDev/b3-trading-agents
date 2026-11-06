from dataclasses import replace
from datetime import date, timedelta

import pytest

from b3desk.data import News, load
from b3desk.research import snapshot


def test_restatement_only_replaces_same_period_after_supplied_availability():
    data = load()
    i = 100
    original = data.filings[0]
    revision = replace(
        original,
        available_on=data.candles[i].date,
        net_income=-original.net_income,
        source="Synthetic revision; availability supplied by test",
    )
    revised = replace(data, filings=(original, revision))
    for at in (i - 1, i):
        assert snapshot(revised, at) == snapshot(replace(data, filings=(original,)), at)
    after = snapshot(revised, i + 1)
    assert after.margin == pytest.approx(-original.net_income / original.revenue)
    assert after.filing_source == revision.source
    assert after.filing_available_on == revision.available_on


def test_news_gate_excludes_same_day_and_future_and_keeps_30_day_boundary(tmp_path):
    data = load()
    i = 100
    today = date.fromisoformat(data.candles[i].date)
    news = tuple(
        News((today - timedelta(days=age)).isoformat(), f"growth {age}", f"synthetic {age}")
        for age in (-1, 0, 1, 30, 31)
    )
    data = replace(data, news=news)
    evidence = snapshot(data, i)
    assert evidence.headlines == ("growth 1", "growth 30")
    assert evidence.news_balance == 2
    # The input JSON, unlike headline-only snapshots, retains each source and date.
    path = tmp_path / "evidence.json"
    data.save(path)
    assert load(path).news == news
    assert snapshot(data, i).target_weight == snapshot(replace(data, news=()), i).target_weight
