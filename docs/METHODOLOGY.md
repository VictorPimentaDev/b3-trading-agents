# Methodology and limitations

This is a transparent reference implementation, not an investment strategy recommendation.
The allocation rules are deliberately simple and were not selected by optimizing a backtest.

## Timeline

A signal for session **t** sees the last 31 closes through **t**, allowing 30 daily returns and a
20-session price change. A filing/news item is eligible only when `available_on < t`. Daily timestamps
cannot prove whether something was released before or after the close, so same-day content is excluded.
The first fill is at the open of session 32. Rebalancing occurs every five sessions by default, using
the preceding close's signal. There is no fill at the signal's own close.

The importer is **not a point-in-time data service**. CVM archives may contain restatements; an accurate
availability date for the particular version is the user's responsibility. Duplicate account rows are
rejected instead of silently choosing a revision. The user must verify the ticker/CD_CVM mapping.
Yahoo adjusted prices can be revised. Causal computation does not fix hindsight in the source data.

## Deterministic allocation

| Condition, evaluated in order | Target |
| --- | --- |
| 20-session momentum ≤ 0 | Cash |
| Annualized sample volatility > 60% | Cash |
| Available net margin < 0 | Cash |
| No available consolidated filing | At most 25% |
| Volatility > 30% | At most 25% |
| Otherwise | At most 50% |

`--max-weight` imposes a further cap. Targets apply when rebalancing; prices can cause exposure to drift
between fills. Shares are whole units, with no 100-share lot requirement (fractional-market approximation).
The model is single-stock plus unremunerated cash, long-only, with no leverage, shorts or derivatives.
Net margin = net income / revenue; ROE = net income / ending equity for the imported fiscal period.
ROE is not annualized, not a trailing-twelve-month series, and does not use average equity.

News is a visible **toy lexical count**, not a trained sentiment model; it is not an allocation input.
The words counted are `growth`, `record`, `crescimento`, `expansão` (+1) and `loss`, `risk`, `queda`,
`risco` (−1), once per word per eligible headline from the last 30 calendar days. Negation and context
are not understood. External narrators can discuss the headlines but cannot change the target.

## Execution, costs and accounting

At a rebalance, the first target is based on the open-marked portfolio. Order size is then solved
against **NAV after fees and slippage**, so the target weight is not exceeded by the transaction
itself. Buys round down and sells round up to whole shares; buys also respect available cash.
For a buy of q shares, the cap is `(existing + q) × open ≤ weight ×
(NAV − brokerage − q × (fill − open + exchange_rate × fill))`. For a sale, use
`(existing − q) × open ≤ weight × (NAV − brokerage − q ×
(open − fill + exchange_rate × fill))`. These caps use the unimpacted opening mark; prices can
subsequently move exposure above target. Buy fills use open × (1 + slippage),
sells use open × (1 − slippage). Brokerage is charged once per nonzero order and exchange fees apply to
executed notional. Positions are marked to that day's close. Cost basis is weighted-average acquisition
cost including buy fees; realized P&L subtracts sell fees. Slippage is included in the fill and is also
reported separately, never deducted a second time. Infeasible cash/cost combinations stop the run.

Default assumptions: **R$4.90 per order, 3.2 bps exchange fees, 5 bps one-way slippage**. Brokerage and
slippage are illustrative assumptions. B3's regular low-volume cash-equity table showed 3.0 bps total
and an additional 0.2 bps trading fee for opening/closing auctions when checked on 2026-11-06. Because
fills are modeled at the open, the default is 3.2 bps. This is not a full B3 invoice engine: verify the
current tier, instrument, auction rules and broker schedule yourself. [Official B3 fee table](https://www.b3.com.br/pt_br/produtos-e-servicos/tarifas/listados-a-vista-e-derivativos/renda-variavel/tarifas-de-acoes-e-fundos-de-investimento/).

**The backtest, CLI/TUI reports, equity curves and benchmark remain pre-tax.** The optional
Python-only IR scenario below produces a separate estimate; it never deducts from the backtest.

Open positions are not liquidated at the end, so closing fees/taxes are absent. Cash earns zero; CDI
opportunity cost matters in Brazil. There is no liquidity/market-impact/partial-fill model, bid/ask book,
corporate-action ledger or investor-specific tax accounting. Imported adjusted OHLC approximates a
reinvested price series and is not a literal historical share/cash ledger. It can introduce bias around
corporate actions. A production execution simulator needs raw prices and explicit corporate actions.

### Optional simplified Brazilian IR scenario

**Estimativa didática de IR, não apuração fiscal. Não é recomendação de investimento.**
`b3desk.taxes.estimate_simplified_ir(result)` explicitly opts into a monthly paper estimate.
No CLI flag or automatic tax deduction is enabled. It returns `SimplifiedIR`, including a warning
label, monthly rows and `estimated_ir_brl` in BRL (`Decimal`). Always retain the label when displaying
or exporting it. The original `Result` and its pre-tax metrics remain unchanged.

```python
from b3desk.backtest import run
from b3desk.data import load
from b3desk.taxes import estimate_simplified_ir

result = run(load())  # Existing synthetic, pre-tax simulation.
estimate = estimate_simplified_ir(result)  # Explicit opt-in; no network calls.
print(estimate.label)
for month in estimate.months:
    print(month)
print("Estimated IR (BRL):", estimate.estimated_ir_brl)
```

Jurisdiction/scenario: a Brazilian resident individual (PF), ordinary long-only cash-equity trades
in one stock, only this simulation's operations, zero starting holdings and zero opening tax losses.
This is not a rule for ETFs, FIIs, BDRs, options, shorts, day trades, legal entities or nonresidents.
The `Result` does not identify asset class or tax residence: the caller must establish these
assumptions. Use only fills produced by `backtest.run()`; this function is not a broker-ledger parser.

Policy reviewed **2026-11-06**, using Receita Federal's pages on
[rates and deductible costs](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/pagamento/renda-variavel/bolsa-de-valores-1/bolsa-de-valores),
[exemptions](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/pagamento/renda-variavel/bolsa-de-valores-1/isencoes) and
[loss compensation](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/pagamento/renda-variavel/bolsa-de-valores-1/compensacoes).
The same fixed assumptions apply to every simulated date; there is no historical law/version engine
or guarantee of applicability before or after that review date. Verify rules for the actual period.

The deterministic calculation is:

1. Group sales by execution calendar month (`YYYY-MM`). Sum gross executed `shares × price` before
   selling fees; buys do not count toward the sales limit. Sum `Trade.realized_pnl`, which already
   includes average acquisition cost, buy/sell fees and slippage through fill prices. Do not subtract
   those costs again. Months without sales have no row and do not consume accumulated losses.
2. Convert the existing float amounts through their decimal strings, sum at decimal precision, and
   round monthly sales and P&L to cents with `ROUND_HALF_UP`. This is a reproducible model convention,
   not a claim to reproduce broker notes or statutory rounding. It cannot restore precision lost in
   the underlying float simulation.
3. A negative monthly P&L adds to the carried loss, including in months with sales up to R$20,000.
   Positive P&L is exempt when monthly gross sales are **at most R$20,000**, preserving prior losses.
   Above that limit, deduct available carried losses from positive net P&L, then estimate **15% of
   the remaining gain**, rounded to cents. The limit is not a deduction from gains. Carry unused
   losses across months and years; subsequent losses never refund earlier estimated tax.

For example, R$21,000 of monthly sales and R$1,500 of realized net gain produce R$225 estimated IR
with no prior losses. With R$1,000 carried loss, the estimate is R$75. At exactly R$20,000 of sales,
the same positive gain is exempt in this scenario. Tests cover the threshold to the cent, monthly
netting, loss carry across a year, exempt gains, cost basis and unchanged pre-tax results.

**Every row is provisional**, including the last month, which can be incomplete. The estimate
assumes no sales elsewhere in the same month. A stock-only run cannot establish an investor-wide
exemption or loss balance. There is no IRRF credit, payment calendar, minimum DARF accumulation,
interest/penalty, dividend/JCP treatment, corporate-action basis adjustment, or tax filing output.
Unrealized gains and terminal liquidation are excluded. Taxes do not reduce trading cash or future
position sizes; subtracting the total from terminal equity would not recreate an after-tax strategy.
The IBOV reference remains untaxed and nontradable, so it is not a like-for-like after-tax benchmark.
Synthetic inputs and adjusted market prices make this unsuitable for real tax reporting even when
the simplified arithmetic matches the stated scenario. Full tax accounting is deliberately deferred
until raw executions, corporate actions and an investor-wide ledger exist.

## Benchmark and metrics

Both series start at the first executable open with the same initial cash. The reference follows
`IBOV_close / first_IBOV_open`, with no trading costs, taxes or tracking error. IBOV itself is not
tradable; this is not a net ETF comparison. Only sessions shared by the stock and index are retained
for imported data. Missing sessions are dropped, never forward-filled into fictitious returns.

Return is final marked equity / starting cash − 1. Drawdown uses the running high including starting
cash. Sharpe uses sample daily standard deviation and √252 with zero risk-free return; its first
interval is open-to-close and later intervals are close-to-close. This is a descriptive statistic, not
an inference of significance. No confidence interval, multiple-testing correction, survival universe,
walk-forward optimization, or claim of outperformance is supplied.

## Data and sources

The packaged fixture uses seed 741 and 220 weekdays from 2024-01-02 to 2024-11-04. Prices, IBOV levels,
financials and headlines are **entirely synthetic**, including holidays that a weekday generator does
not remove. `WEGE3` names an example instrument; none of these observations are WEG facts. Regenerate
with `uv run python scripts/make_fixture.py`. No external dataset is redistributed in the fixture.

Live imports are optional. [CVM DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp) provides the
consolidated DRE/BPP input format and carries its own data license (ODbL at the time of review).
The importer reads `3.01` revenue, `3.11` net income, and `2.03` equity, `ÚLTIMO` period rows,
`REAL` currency and `MIL`/`UNIDADE` units. Banks and issuers with different account structures may be
rejected; the application does not silently substitute other measures.
[yfinance](https://ranaroussi.github.io/yfinance/) is an unofficial Yahoo Finance client; review the
underlying data terms before using or redistributing downloads.
