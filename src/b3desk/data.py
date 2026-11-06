"""Validated, point-in-time research inputs. No implicit live network calls."""

import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from importlib.resources import files
from pathlib import Path


def calendar_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD format")
    return parsed


@dataclass(frozen=True)
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    ibov_open: float
    ibov_close: float

    def __post_init__(self):
        calendar_date(self.date)
        values = (self.open, self.high, self.low, self.close, self.ibov_open, self.ibov_close)
        if any(not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("Prices must be finite and positive")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("Invalid OHLC bounds")
        if not isinstance(self.volume, int) or self.volume < 0:
            raise ValueError("Volume must be a nonnegative integer")


@dataclass(frozen=True)
class Filing:
    period_end: str
    available_on: str
    revenue: float
    net_income: float
    equity: float
    source: str

    def __post_init__(self):
        if calendar_date(self.available_on) < calendar_date(self.period_end):
            raise ValueError("A filing cannot be available before its period ends")
        if any(not math.isfinite(v) for v in (self.revenue, self.net_income, self.equity)):
            raise ValueError("Filing values must be finite")
        if self.revenue <= 0 or self.equity <= 0 or not self.source.strip():
            raise ValueError("This research model requires positive revenue/equity and a source")


@dataclass(frozen=True)
class News:
    available_on: str
    headline: str
    source: str

    def __post_init__(self):
        calendar_date(self.available_on)
        if not self.headline.strip() or not self.source.strip():
            raise ValueError("News needs a headline and source")


@dataclass(frozen=True)
class Dataset:
    ticker: str
    description: str
    synthetic: bool
    candles: tuple[Candle, ...]
    filings: tuple[Filing, ...]
    news: tuple[News, ...]

    def __post_init__(self):
        if not self.ticker or not self.description or type(self.synthetic) is not bool:
            raise ValueError("Dataset needs ticker, description and explicit synthetic flag")
        dates = [c.date for c in self.candles]
        if len(dates) < 32 or dates != sorted(set(dates)):
            raise ValueError("At least 32 unique, ascending candles are required")
        keys = [(f.period_end, f.available_on) for f in self.filings]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate filing period and availability date")

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n")


def load(path: Path | None = None) -> Dataset:
    raw = path.read_text() if path else files("b3desk").joinpath("fixtures/demo.json").read_text()
    data = json.loads(raw)
    return Dataset(
        ticker=data["ticker"],
        description=data["description"],
        synthetic=data["synthetic"],
        candles=tuple(Candle(**c) for c in data["candles"]),
        filings=tuple(Filing(**f) for f in data["filings"]),
        news=tuple(News(**n) for n in data["news"]),
    )
