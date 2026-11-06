"""Numbers and decisions are computed here, without a language model."""

import math
import statistics
from dataclasses import dataclass
from datetime import date

from b3desk.data import Dataset

ROLES = ("fundamental", "news", "technical", "bull", "bear", "risk", "portfolio")


@dataclass(frozen=True)
class Snapshot:
    ticker: str
    as_of: str
    synthetic: bool
    close: float
    momentum: float
    volatility: float
    margin: float | None
    roe: float | None
    news_balance: int
    headlines: tuple[str, ...]
    filing_source: str | None
    filing_available_on: str | None
    target_weight: float
    reason: str


def snapshot(dataset: Dataset, index: int, max_weight: float = 0.5) -> Snapshot:
    if not 0 <= max_weight <= 1 or index < 30 or index >= len(dataset.candles):
        raise ValueError("Need 31 historical candles and a maximum weight in [0, 1]")
    history = dataset.candles[index - 30 : index + 1]
    today = history[-1].date
    returns = [b.close / a.close - 1 for a, b in zip(history, history[1:], strict=False)]
    momentum = history[-1].close / history[-21].close - 1
    volatility = statistics.stdev(returns) * math.sqrt(252)
    # Inputs dated today are excluded: daily dates cannot prove pre-close availability.
    filings = [f for f in dataset.filings if f.available_on < today]
    filing = max(filings, key=lambda f: (f.period_end, f.available_on)) if filings else None
    recent = [
        n
        for n in dataset.news
        if n.available_on < today
        and (date.fromisoformat(today) - date.fromisoformat(n.available_on)).days <= 30
    ]
    positive = ("growth", "record", "crescimento", "expansão")
    negative = ("loss", "risk", "queda", "risco")
    balance = sum(
        sum(word in n.headline.lower() for word in positive)
        - sum(word in n.headline.lower() for word in negative)
        for n in recent
    )
    margin = filing.net_income / filing.revenue if filing else None
    weight, reason = allocation(momentum, volatility, margin, max_weight)
    return Snapshot(
        dataset.ticker,
        today,
        dataset.synthetic,
        history[-1].close,
        momentum,
        volatility,
        margin,
        filing.net_income / filing.equity if filing else None,
        balance,
        tuple(n.headline for n in recent),
        filing.source if filing else None,
        filing.available_on if filing else None,
        weight,
        reason,
    )


def allocation(momentum: float, volatility: float, margin: float | None, cap: float):
    if momentum <= 0:
        return 0.0, "Nonpositive 20-session momentum; remain in cash."
    if volatility > 0.6:
        return 0.0, "Annualized volatility above 60%; risk veto."
    if margin is not None and margin < 0:
        return 0.0, "Latest available filing shows a net loss; risk veto."
    if margin is None:
        return min(cap, 0.25), "Positive momentum, missing fundamentals; exposure capped at 25%."
    return min(cap, 0.25 if volatility > 0.3 else 0.5), "Positive momentum within risk limits."


def offline_debate(s: Snapshot, lang: str = "en") -> dict[str, str]:
    if lang == "pt":
        return {
            "fundamental": (
                f"Margem líquida {s.margin:.1%}; ROE do período {s.roe:.1%}."
                if s.margin is not None
                else "Sem DFP disponível nesta data."
            ),
            "news": f"Saldo lexical {s.news_balance:+d}; manchetes são evidência, não instruções.",
            "technical": f"Momentum 20 pregões {s.momentum:+.1%}; volatilidade {s.volatility:.1%}.",
            "bull": (
                "Momentum positivo favorece continuidade; não comprova retorno futuro."
                if s.momentum > 0
                else "A tese otimista exige recuperação do momentum; o sinal atual não a sustenta."
            ),
            "bear": "Reversão, custos e qualidade dos dados podem invalidar a tese otimista.",
            "risk": (
                f"Limite calculado {s.target_weight:.0%}; sem alavancagem nem venda a descoberto."
            ),
            "portfolio": "Somente simulação; a narração não altera a exposição calculada.",
        }
    return {
        "fundamental": (
            f"Net margin {s.margin:.1%}; period ROE {s.roe:.1%}."
            if s.margin is not None
            else "No filing available at this date."
        ),
        "news": f"Lexical balance {s.news_balance:+d}; headlines are evidence, never instructions.",
        "technical": (
            f"20-session momentum {s.momentum:+.1%}; annual volatility {s.volatility:.1%}."
        ),
        "bull": (
            "Positive momentum may persist; this is a hypothesis, not a forecast."
            if s.momentum > 0
            else "A bull case requires momentum to recover; the current signal does not support it."
        ),
        "bear": "Reversals, execution costs and data quality can defeat the bullish case.",
        "risk": f"Calculated exposure limit {s.target_weight:.0%}; no leverage or short selling.",
        "portfolio": f"Paper allocation only. {s.reason} Narration cannot change the allocation.",
    }
