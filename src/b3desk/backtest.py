"""Close-time signal, next-open fill, integer shares, explicit friction."""

import math
import statistics
from dataclasses import asdict, dataclass

from b3desk.data import Dataset
from b3desk.research import snapshot


@dataclass(frozen=True)
class Costs:
    brokerage: float = 4.90
    exchange_bps: float = 3.2
    slippage_bps: float = 5.0

    def __post_init__(self):
        if any(not math.isfinite(v) or v < 0 for v in asdict(self).values()):
            raise ValueError("Costs must be finite and nonnegative")
        if self.slippage_bps >= 10000:
            raise ValueError("Slippage must be below 100%")

    def fee(self, notional: float) -> float:
        return self.brokerage + notional * self.exchange_bps / 10000 if notional else 0.0


@dataclass(frozen=True)
class Trade:
    date: str
    signal_date: str
    side: str
    shares: int
    price: float
    fees: float
    realized_pnl: float


@dataclass(frozen=True)
class Result:
    dates: tuple[str, ...]
    equity: tuple[float, ...]
    benchmark: tuple[float, ...]
    exposure: tuple[float, ...]
    trades: tuple[Trade, ...]
    initial_cash: float
    costs: Costs
    max_weight: float
    rebalance: int

    @property
    def metrics(self):
        returns = [b / a - 1 for a, b in zip(self.equity, self.equity[1:], strict=False)]
        peak, drawdown = self.initial_cash, 0.0
        for equity in self.equity:
            peak = max(peak, equity)
            drawdown = min(drawdown, equity / peak - 1)
        vol = statistics.stdev(returns) if len(returns) > 1 else 0
        return {
            "return": self.equity[-1] / self.initial_cash - 1,
            "ibov_return": self.benchmark[-1] / self.initial_cash - 1,
            "max_drawdown": drawdown,
            "sharpe_zero_rf": statistics.mean(returns) / vol * math.sqrt(252) if vol else 0.0,
            "fees_brl": sum(t.fees for t in self.trades),
            "slippage_brl": sum(
                t.shares
                * t.price
                / (1 + (1 if t.side == "BUY" else -1) * self.costs.slippage_bps / 10000)
                * self.costs.slippage_bps
                / 10000
                for t in self.trades
            ),
            "trades": len(self.trades),
        }


DEFAULT_COSTS = Costs()


def run(
    dataset: Dataset,
    cash: float = 100_000,
    costs: Costs = DEFAULT_COSTS,
    max_weight: float = 0.5,
    rebalance: int = 5,
) -> Result:
    if (
        not math.isfinite(cash)
        or cash <= 0
        or not isinstance(rebalance, int)
        or rebalance < 1
        or not 0 <= max_weight <= 1
    ):
        raise ValueError("Positive cash/rebalance and maximum weight in [0, 1] required")
    initial, shares, basis = cash, 0, 0.0
    dates, equities, benchmarks, exposures, trades = [], [], [], [], []
    first = dataset.candles[31]
    # Baseline is the execution-date open, before any purchase or fee.
    dates.append(first.date + " open")
    equities.append(cash)
    benchmarks.append(cash)
    exposures.append(0.0)
    for i in range(31, len(dataset.candles)):
        candle = dataset.candles[i]
        if (i - 31) % rebalance == 0:
            weight = snapshot(dataset, i - 1, max_weight).target_weight
            nav = cash + shares * candle.open
            target = math.floor(nav * weight / candle.open)
            delta = target - shares
            price = candle.open * (1 + (1 if delta > 0 else -1) * costs.slippage_bps / 10000)
            if delta > 0:
                drag = price - candle.open + price * costs.exchange_bps / 10000
                # Solve the exposure cap against NAV after this order's fees and slippage.
                delta = max(
                    0,
                    math.floor(
                        (weight * (nav - costs.brokerage) - shares * candle.open)
                        / (candle.open + weight * drag)
                    ),
                )
                affordable = math.floor(
                    max(0, cash - costs.brokerage) / (price * (1 + costs.exchange_bps / 10000))
                )
                delta = min(delta, affordable)
            elif delta < 0:
                drag = candle.open - price + price * costs.exchange_bps / 10000
                denominator = candle.open - weight * drag
                if denominator <= 0:
                    raise ValueError("Trading costs make the exposure target infeasible")
                delta = -min(
                    shares,
                    math.ceil(
                        (shares * candle.open - weight * (nav - costs.brokerage)) / denominator
                    ),
                )
            if delta:
                notional = abs(delta) * price
                fee = costs.fee(notional)
                pnl = 0.0 if delta > 0 else -delta * (price - basis) - fee
                if delta > 0:
                    basis = (shares * basis + notional + fee) / (shares + delta)
                if cash - delta * price - fee < -1e-8:
                    raise ValueError("Trading costs exceed available cash; simulation stopped")
                cash = max(0.0, cash - delta * price - fee)
                shares += delta
                if shares == 0:
                    basis = 0.0
                trades.append(
                    Trade(
                        candle.date,
                        dataset.candles[i - 1].date,
                        "BUY" if delta > 0 else "SELL",
                        abs(delta),
                        price,
                        fee,
                        pnl,
                    )
                )
        equity = cash + shares * candle.close
        dates.append(candle.date)
        equities.append(equity)
        benchmarks.append(initial * candle.ibov_close / first.ibov_open)
        exposures.append(shares * candle.close / equity)
    return Result(
        tuple(dates),
        tuple(equities),
        tuple(benchmarks),
        tuple(exposures),
        tuple(trades),
        initial,
        costs,
        max_weight,
        rebalance,
    )
