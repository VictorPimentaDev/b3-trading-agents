"""Create explicitly synthetic inputs; never a source of claimed market performance."""

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(741)
current, price, ibov = date(2024, 1, 2), 36.0, 130_000.0
candles = []
while len(candles) < 220:
    if current.weekday() < 5:
        i = len(candles)
        regime = 0.002 if i < 90 or i > 150 else -0.0014
        opening = price * math.exp(rng.gauss(0, 0.003))
        price = opening * math.exp(regime + rng.gauss(0, 0.012))
        ibov_open = ibov * math.exp(rng.gauss(0, 0.002))
        ibov = ibov_open * math.exp(0.0001 + rng.gauss(0, 0.008))
        candles.append(
            dict(
                date=current.isoformat(),
                open=round(opening, 4),
                high=round(max(opening, price) * 1.006, 4),
                low=round(min(opening, price) * 0.994, 4),
                close=round(price, 4),
                volume=rng.randint(500_000, 4_000_000),
                ibov_open=round(ibov_open, 4),
                ibov_close=round(ibov, 4),
            )
        )
    current += timedelta(days=1)
fixture = dict(
    ticker="WEGE3",
    synthetic=True,
    description="SYNTHETIC teaching fixture. Not WEG or IBOV historical prices/financials. "
    "Weekdays only, not a B3 holiday calendar. Seed 741.",
    candles=candles,
    filings=[
        dict(
            period_end="2023-12-31",
            available_on="2024-03-01",
            revenue=32e9,
            net_income=4.8e9,
            equity=20e9,
            source="Synthetic DFP-shaped example; not WEG data",
        )
    ],
    news=[
        dict(
            available_on="2024-10-01",
            headline="Synthetic: growth in industrial orders",
            source="Synthetic editorial example",
        ),
        dict(
            available_on="2024-10-15",
            headline="Synthetic: currency risk remains",
            source="Synthetic editorial example",
        ),
    ],
)
Path("src/b3desk/fixtures/demo.json").write_text(json.dumps(fixture, indent=2) + "\n")
