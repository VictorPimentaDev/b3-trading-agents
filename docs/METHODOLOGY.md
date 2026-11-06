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

**All results are pre-tax.** There is no simplified income-tax deduction disguised as a complete IR
calculation. Monthly exemptions, loss carryforwards, withholding, day-trade distinctions and other
holdings are not modeled. [Receita Federal: net gains](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/pagamento/renda-variavel/bolsa-de-valores-1/ganho-liquido).

Open positions are not liquidated at the end, so closing fees/taxes are absent. Cash earns zero; CDI
opportunity cost matters in Brazil. There is no liquidity/market-impact/partial-fill model, bid/ask book,
corporate-action ledger or investor-specific tax accounting. Imported adjusted OHLC approximates a
reinvested price series and is not a literal historical share/cash ledger. It can introduce bias around
corporate actions. A production execution simulator needs raw prices and explicit corporate actions.

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
