"""Draw the offer-grid illustration and agreement rates from the saved simulations."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle
from matplotlib.ticker import PercentFormatter
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
BIN_EDGES = [0, .2, .4, .6, .8, 1]
BIN_LABELS = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]
WIDTHS = (1, 2, 3)
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "savefig.facecolor": "white",
})


def save(figure, name):
    RESULTS.mkdir(exist_ok=True)
    for extension in ("png", "pdf"):
        figure.savefig(RESULTS / f"{name}.{extension}", dpi=300, bbox_inches="tight")
    plt.close(figure)


def draw_offer_grid(axis, *, wide, high_complexity):
    # Coordinates and paths follow the manuscript illustration. Both paths end
    # at (4, 7), inside either low-complexity zone and outside either high one.
    first = [(1, 2), (2, 2), (2, 3), (3, 3), (3, 4), (2, 4),
             (2, 5), (3, 5), (3, 6), (3, 7), (4, 7)]
    second = [(8, 8), (8, 9), (7, 9), (7, 8), (6, 8), (6, 9),
              (5, 9), (5, 8), (4, 8), (4, 7)]
    start_x, start_y = (6, 0) if high_complexity else (4, 3)
    width = 4 if wide else 2
    axis.add_patch(Rectangle((start_x - .5, start_y - .5), width, 5,
                             facecolor=".79", edgecolor="none"))
    for edge in range(1, 10):
        axis.axhline(edge - .5, color=".86", linewidth=.45, zorder=1)
        axis.axvline(edge - .5, color=".86", linewidth=.45, zorder=1)
    for path, color, linestyle in [(first, ".06", "-"), (second, ".53", "--")]:
        x, y = zip(*path)
        axis.plot(x, y, color=color, linestyle=linestyle, linewidth=1.75,
                  marker="o", markersize=3.3, zorder=3)
        axis.plot(x[0], y[0], marker="*", markersize=11, color=color, zorder=4)

    if high_complexity:
        # No offer in either high-complexity zone shares a row or column with
        # the stopping point. This example changes both issues to reach it.
        axis.add_patch(FancyArrowPatch(
            (4, 7), (6, 4), arrowstyle="-|>", shrinkA=7, shrinkB=3,
            linestyle=":", linewidth=1.7, color=".15", mutation_scale=13, zorder=5,
        ))
        axis.plot(4, 7, marker="X", markersize=9, color=".06",
                  markeredgecolor="white", markeredgewidth=.65, zorder=6)
    else:
        axis.plot(4, 7, marker="o", markersize=10, markerfacecolor="white",
                  markeredgewidth=1.35, markeredgecolor=".06", zorder=5)
        axis.plot(4, 7, marker="o", markersize=4.3, color=".06", zorder=6)

    axis.text(start_x + (width - 1) / 2, start_y + 1.15, f"{width * 5} / 100",
              ha="center", va="center", fontsize=9, fontweight="bold")
    axis.set(xlim=(-.5, 9.5), ylim=(-.5, 9.5), xticks=[], yticks=[], aspect="equal")
    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_color(".1")
        spine.set_linewidth(1)


def illustrate_search():
    fig, axes = plt.subplots(2, 2, figsize=(7.15, 7.18))
    for row, high in enumerate((False, True)):
        for column, wide in enumerate((False, True)):
            draw_offer_grid(axes[row, column], wide=wide, high_complexity=high)
        row_label = "High search\ncomplexity" if high else "Low search\ncomplexity"
        axes[row, 0].text(-.09, .5, row_label, transform=axes[row, 0].transAxes,
                          ha="right", va="center", fontsize=11, fontweight="bold")
    for axis, title in zip(axes[0], ["Small bargaining zone", "Wide bargaining zone"]):
        axis.set_title(title, fontsize=11, fontweight="bold", pad=8)

    items = [
        Line2D([], [], marker="*", color=".06", linestyle="none", markersize=9,
               label="Starting offer"),
        Line2D([], [], color=".06", linewidth=1.75, label="Party 1"),
        Line2D([], [], color=".53", linestyle="--", linewidth=1.75, label="Party 2"),
        Patch(facecolor=".79", edgecolor=".62", label="Bargaining zone"),
        Line2D([], [], marker=r"$\odot$", color=".06", linestyle="none",
               markersize=10, label="Agreement"),
        Line2D([], [], marker="X", color=".06", linestyle="none", markersize=7,
               label="Local impasse"),
        Line2D([], [], color=".15", linestyle=":", linewidth=1.7,
               label="Change both issues"),
    ]
    fig.subplots_adjust(left=.19, right=.97, top=.95, bottom=.116, wspace=.10, hspace=.11)
    fig.legend(handles=items, loc="lower center", bbox_to_anchor=(.535, .015), ncol=4,
               frameon=False, fontsize=8.6, columnspacing=1.20, handletextpad=.5)
    save(fig, "figure_1_search_example")


def summarize(parties):
    suffix = "_two_party" if parties == 2 else ""
    runs = pd.read_csv(ROOT / "data" / f"simulation_conditions{suffix}.csv")
    rates = runs.pivot(index="scenario_index", columns="search_distance", values="agreement_rate")
    if list(rates.columns) != list(WIDTHS) or len(rates) != 1000 or rates.isna().any().any():
        raise ValueError("Expected the same 1,000 negotiations under each of the three rules.")
    complexity = runs[["scenario_index", "search_complexity"]].drop_duplicates()
    complexity = complexity.set_index("scenario_index")["search_complexity"]
    if not complexity.index.is_unique:
        raise ValueError("Search complexity differs across search rules for a negotiation.")
    bins = pd.cut(complexity, BIN_EDGES, labels=BIN_LABELS, include_lowest=True)
    grouped = rates.groupby(bins, observed=True)
    means = grouped.mean().reindex(BIN_LABELS)
    return pd.DataFrame({
        "parties": parties,
        "search_complexity_bin": BIN_LABELS,
        "structures": grouped.size().reindex(BIN_LABELS, fill_value=0).to_numpy(),
        "one_issue_agreement_rate": means[1].to_numpy(),
        "up_to_two_agreement_rate": means[2].to_numpy(),
        "up_to_three_agreement_rate": means[3].to_numpy(),
    })


def plot_agreement(estimates, *, title, file_name):
    fig, axis = plt.subplots(figsize=(6.6, 3.85), layout="constrained")
    # Draw wider-search lines first so the black baseline stays easy to find.
    series = [
        ("up_to_three_agreement_rate", "Up to three issues", ".46", ":", "^"),
        ("up_to_two_agreement_rate", "Up to two issues", ".31", "--", "s"),
        ("one_issue_agreement_rate", "One issue", ".05", "-", "o"),
    ]
    for column, label, tone, style, marker in series:
        axis.plot(range(len(BIN_LABELS)), 100 * estimates[column], label=label,
                  color=tone, linestyle=style, linewidth=1.65, marker=marker,
                  markersize=5, markerfacecolor="white")
    axis.set(title=title, xlabel="Search complexity", ylabel="Agreement rate",
             xlim=(-.18, 4.18), ylim=(0, 104), yticks=(0, 25, 50, 75, 100))
    axis.set_xticks(range(len(BIN_LABELS)), BIN_LABELS, fontsize=9)
    axis.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    axis.grid(False)
    handles, labels = axis.get_legend_handles_labels()
    axis.legend(handles[::-1], labels[::-1], loc="lower left", frameon=False,
                fontsize=9, handlelength=2.6)
    save(fig, file_name)


if __name__ == "__main__":
    illustrate_search()
    six = summarize(6)
    two = summarize(2)
    pd.concat([six, two]).to_csv(RESULTS / "figure_2_estimates.csv", index=False,
                                float_format="%.8f")
    plot_agreement(six, title="Six-party negotiations", file_name="figure_2_simulated_agreement")
    plot_agreement(two, title="Two-party negotiations", file_name="appendix_figure_two_party")
