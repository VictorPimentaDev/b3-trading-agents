"""Opt-in external data imports; imported datasets remain reviewable JSON."""

import csv
import io
import re
import zipfile
from datetime import date
from pathlib import Path

from b3desk.data import Candle, Dataset, Filing


def market(ticker: str, start: str, end: str) -> Dataset:
    if not re.fullmatch(r"[A-Z]{4}[0-9]{1,2}", ticker):
        raise ValueError("Expected a B3 equity ticker, e.g. WEGE3")
    if date.fromisoformat(start) >= date.fromisoformat(end):
        raise ValueError("Start must precede end (end is exclusive)")
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ValueError("Install market support: pip install -e '.[market]'") from exc
    prices = yf.Ticker(ticker + ".SA").history(start=start, end=end, auto_adjust=True)
    index = yf.Ticker("^BVSP").history(start=start, end=end, auto_adjust=True)
    if prices.empty or index.empty:
        raise ValueError("Market source returned no prices")
    lookup = {str(d.date()): row for d, row in index.iterrows()}
    candles = []
    for d, row in prices.iterrows():
        key = str(d.date())
        if key in lookup:
            benchmark = lookup[key]
            candles.append(
                Candle(
                    key,
                    float(row.Open),
                    float(row.High),
                    float(row.Low),
                    float(row.Close),
                    int(row.Volume),
                    float(benchmark.Open),
                    float(benchmark.Close),
                )
            )
    return Dataset(
        ticker,
        "Yahoo Finance via yfinance; adjusted OHLC, ^BVSP intersection. "
        "Downloaded " + date.today().isoformat() + ". Not point-in-time snapshots.",
        False,
        tuple(candles),
        (),
        (),
    )


def cvm_filing(archive: Path, cvm_code: int, period: str, available_on: str) -> Filing:
    """Read consolidated DFP revenue/profit/equity; reject ambiguous revisions."""
    date.fromisoformat(period)
    date.fromisoformat(available_on)
    wanted = {"DRE": {"3.01": "revenue", "3.11": "net_income"}, "BPP": {"2.03": "equity"}}
    values = {}
    with zipfile.ZipFile(archive) as bundle:
        for statement, accounts in wanted.items():
            matches = [
                n for n in bundle.namelist() if f"_{statement}_con_" in n and n.endswith(".csv")
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one consolidated {statement} CSV")
            with bundle.open(matches[0]) as stream:
                rows = csv.DictReader(io.TextIOWrapper(stream, encoding="latin-1"), delimiter=";")
                for row in rows:
                    if (
                        int(row["CD_CVM"]) != cvm_code
                        or row["DT_REFER"] != period
                        or row["DT_FIM_EXERC"] != period
                        or row["ORDEM_EXERC"] != "ÚLTIMO"
                        or row["CD_CONTA"] not in accounts
                    ):
                        continue
                    key = accounts[row["CD_CONTA"]]
                    if key in values:
                        raise ValueError("Ambiguous account/revision; provide a single DFP version")
                    if row["ESCALA_MOEDA"] not in ("MIL", "UNIDADE") or row["MOEDA"] != "REAL":
                        raise ValueError("Only REAL in MIL/UNIDADE units is supported")
                    factor = 1000 if row["ESCALA_MOEDA"] == "MIL" else 1
                    values[key] = float(row["VL_CONTA"].replace(",", ".")) * factor
    if set(values) != {"revenue", "net_income", "equity"}:
        raise ValueError("Missing required consolidated DFP accounts for this company/period")
    return Filing(
        period,
        available_on,
        **values,
        source=f"CVM DFP {archive.name}; CD_CVM={cvm_code}; availability supplied by user",
    )
