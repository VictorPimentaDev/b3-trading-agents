# Contributing

Start with an issue that includes the smallest reproducible input and the observed output.
This is a research tool; a profitable chart alone is not evidence that a change is correct.

```sh
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

For a backtest change, include a hand-calculated example and a future-data perturbation test.
For a provider change, use `httpx.MockTransport`; CI must work without API keys or model downloads.
For a data adapter, preserve source, units, revision and availability timestamps. Do not commit
licensed market data without redistribution rights, credentials, private filings or personal data.

Useful first contributions: add a CSV export of the existing trade ledger; add screen-reader-friendly
plain-text output; extend CVM fixtures to cover restated reports. Please discuss changes to allocation
rules before implementing them so the methodology and tests stay in agreement.

The implementation is MIT. Upstream datasets and model services have their own terms.
