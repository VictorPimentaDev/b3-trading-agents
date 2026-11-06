"""Headless report rendering, shared by CLI and documentation."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

from b3desk.backtest import Result  # noqa: E402


def chart(result: Result, target: Path, synthetic: bool = True):
    with plt.rc_context(
        {
            "font.family": "monospace",
            "text.color": "#e2e8f0",
            "axes.labelcolor": "#94a3b8",
            "xtick.color": "#94a3b8",
            "ytick.color": "#94a3b8",
            "font.size": 10,
        }
    ):
        fig, (ax, exposure) = plt.subplots(
            2, 1, figsize=(12, 6.3), sharex=True, gridspec_kw={"height_ratios": [4, 1]}
        )
        fig.set_facecolor("#0b1220")
        fig.suptitle("B3 / RESEARCH DESK", x=0.08, ha="left", fontsize=23, weight="bold")
        subtitle = (
            "SYNTHETIC DEMO • NO HISTORICAL PERFORMANCE"
            if synthetic
            else "PAPER RESEARCH • PRE-TAX"
        )
        ax.set_title(subtitle, loc="left", color="#fbbf24", fontsize=10, pad=20)
        for panel in (ax, exposure):
            panel.set_facecolor("#0b1220")
            panel.grid(axis="y", color="#233044", linewidth=0.6)
            for spine in panel.spines.values():
                spine.set_visible(False)
        ax.plot(
            [e / result.initial_cash - 1 for e in result.equity],
            color="#5eead4",
            linewidth=2.2,
            label="Rules + costs",
        )
        ax.plot(
            [e / result.initial_cash - 1 for e in result.benchmark],
            color="#94a3b8",
            linewidth=1.4,
            label="IBOV reference (gross)",
        )
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend(facecolor="#0b1220", edgecolor="none", labelcolor="#e2e8f0", loc="upper left")
        exposure.fill_between(
            range(len(result.exposure)), result.exposure, color="#5eead4", alpha=0.3
        )
        exposure.set_ylim(0, 1)
        exposure.yaxis.set_major_formatter(PercentFormatter(1))
        exposure.set_ylabel("Exposure")
        points = [0, len(result.dates) // 2, len(result.dates) - 1]
        exposure.set_xticks(points, [result.dates[i][:10] for i in points])
        fig.text(
            0.08,
            0.025,
            "Python calculates. Models narrate.   /   NOT INVESTMENT ADVICE",
            color="#94a3b8",
            fontsize=9,
        )
        fig.subplots_adjust(left=0.08, right=0.96, top=0.8, bottom=0.12, hspace=0.13)
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
