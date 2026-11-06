"""Command line entry points. The default demo makes zero network requests."""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from b3desk.backtest import Costs, run
from b3desk.charts import chart
from b3desk.data import load
from b3desk.importers import cvm_filing, market
from b3desk.presentation import discussion, overview
from b3desk.providers import debate
from b3desk.research import snapshot


def parser():
    root = argparse.ArgumentParser(
        description="B3 research desk. Paper only; not investment advice."
    )
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("demo", "backtest", "analyze", "tui"):
        p = sub.add_parser(name)
        p.add_argument(
            "--data", type=Path, help="Validated dataset JSON (default: synthetic fixture)"
        )
        p.add_argument("--cash", type=float, default=100_000)
        p.add_argument("--brokerage", type=float, default=4.9)
        p.add_argument("--exchange-bps", type=float, default=3.2)
        p.add_argument("--slippage-bps", type=float, default=5)
        p.add_argument("--max-weight", type=float, default=0.5)
        p.add_argument("--rebalance", type=int, default=5)
        if name != "tui":
            p.add_argument("--out", type=Path, default=Path("output"))
            p.add_argument("--lang", choices=("en", "pt"), default="en")
            p.add_argument(
                "--provider",
                choices=("offline", "openai", "anthropic", "ollama"),
                default="offline",
            )
            p.add_argument("--model", default="", help="Explicit model name for network narration")
    fetch = sub.add_parser("fetch", help="Opt-in Yahoo Finance OHLC + IBOV import")
    fetch.add_argument("--ticker", required=True)
    fetch.add_argument("--start", required=True)
    fetch.add_argument("--end", required=True)
    fetch.add_argument("--out", type=Path, required=True)
    cvm = sub.add_parser("import-cvm", help="Add one consolidated filing from an official DFP ZIP")
    cvm.add_argument("--data", type=Path, required=True)
    cvm.add_argument("--zip", type=Path, required=True)
    cvm.add_argument("--cvm-code", type=int, required=True)
    cvm.add_argument("--period", required=True)
    cvm.add_argument("--available-on", required=True, help="Verified publication/availability date")
    cvm.add_argument("--out", type=Path, required=True)
    return root


def execute(args, console: Console):
    if args.command == "fetch":
        market(args.ticker, args.start, args.end).save(args.out)
        console.print(f"Saved imported market dataset to {args.out}")
        return
    if args.command == "import-cvm":
        dataset = load(args.data)
        if dataset.synthetic:
            raise ValueError(
                "Do not mix real filings into synthetic prices; fetch market data first"
            )
        filing = cvm_filing(args.zip, args.cvm_code, args.period, args.available_on)
        replace(dataset, filings=(*dataset.filings, filing)).save(args.out)
        console.print(f"Saved filing to {args.out}; verify ticker ↔ CD_CVM mapping manually")
        return
    dataset = load(args.data)
    costs = Costs(args.brokerage, args.exchange_bps, args.slippage_bps)
    result = run(dataset, args.cash, costs, args.max_weight, args.rebalance)
    evidence = snapshot(dataset, len(dataset.candles) - 1, args.max_weight)
    if args.command == "tui":
        from b3desk.tui import Desk

        args_out = Path("output")
        args_out.mkdir(exist_ok=True)
        Desk(evidence, result).run()
        return
    transcript = debate(evidence, args.provider, args.model, args.lang)
    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        "disclaimer": "Research only. Not investment advice. Não é recomendação de investimento.",
        "dataset": dataset.description,
        "snapshot": asdict(evidence),
        "backtest": asdict(result),
        "metrics": result.metrics,
        "narration_provider": args.provider,
        "narration_model": args.model,
        "narration": transcript,
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    chart(result, args.out / "equity.png", dataset.synthetic)
    console.print(Panel(overview(evidence, result), title="B3 / RESEARCH DESK"))
    if args.command != "backtest":
        console.print(discussion(transcript))
    console.print(
        "[yellow]Research only. Not investment advice. Não é recomendação de investimento.[/]"
    )
    console.print(f"Saved {args.out / 'report.json'} and {args.out / 'equity.png'}")


def main(argv=None):
    args = parser().parse_args(argv)
    console = Console()
    try:
        execute(args, console)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        console.print(f"[red]Error:[/] {exc}", markup=False)
        return 2
    return 0
