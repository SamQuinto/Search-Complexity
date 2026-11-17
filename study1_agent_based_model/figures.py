"""Draw Figures 1 and 2 from the illustrative example and saved model runs."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.ticker import PercentFormatter
import pandas as pd


ROOT = Path(__file__).resolve().parent
COLORS = {1: "#4B5563", 2: "#23756C", 3: "#1F5182"}
plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "savefig.facecolor": "white",
})


def save(figure, name):
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    for extension in ("png", "pdf"):
        figure.savefig(results / f"{name}.{extension}", dpi=270, bbox_inches="tight")
    plt.close(figure)


def illustrate_search():
    fig, ax = plt.subplots(figsize=(7.8, 3.9))
    offers = {
        "Starting offer": ((0, 0), 2),
        "Change issue 1": ((1, 0), 1),
        "Change issue 2": ((0, 1), 1),
        "Agreement": ((1, 1), 3),
    }
    for start, end in [((0, 0), (1, 0)), ((0, 0), (0, 1)),
                       ((1, 0), (1, 1)), ((0, 1), (1, 1))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-", shrinkA=31, shrinkB=31,
                                     linewidth=1.6, color="#A1A7AD", linestyle="--"))
    ax.add_patch(FancyArrowPatch((0, 0), (1, 1), arrowstyle="-|>", shrinkA=31,
                                 shrinkB=31, linewidth=2.2, color=COLORS[3],
                                 mutation_scale=17))
    for title, ((x, y), count) in offers.items():
        color = COLORS[3] if count == 3 else "#4B5563"
        ax.scatter(x, y, s=1750, color="white", edgecolor=color, linewidths=1.8, zorder=3)
        ax.text(x, y, f"{count} of 3", ha="center", va="center", color=color,
                weight="bold", zorder=4)
        offset = 0.19 if y else -0.19
        ax.text(x, y + offset, title, ha="center", va="bottom" if y else "top")
    ax.text(.48, .46, "Two-issue change", ha="center", va="center", color=COLORS[3],
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 3})
    ax.set(xlim=(-.31, 1.31), ylim=(-.30, 1.30))
    ax.axis("off")
    save(fig, "figure_1_search_example")


def summarize():
    runs = pd.read_csv(ROOT / "data" / "simulation_conditions.csv")
    rates = runs.pivot(index="scenario_index", columns="search_distance",
                      values="agreement_rate")
    if list(rates.columns) != [1, 2, 3] or len(rates) != 1000 or rates.isna().any().any():
        raise ValueError("Expected the same 1,000 negotiations under each of the three search rules.")
    structures = (runs[["scenario_index", "search_complexity"]].drop_duplicates()
                  .set_index("scenario_index").sort_values("search_complexity", kind="stable"))
    levels = pd.qcut(structures["search_complexity"].rank(method="first"), 5, labels=False) + 1
    rates["complexity_fifth"] = levels
    means = rates.groupby("complexity_fifth").mean()
    estimates = pd.DataFrame({
        "complexity_fifth": means.index,
        "structures": rates.groupby("complexity_fifth").size().to_numpy(),
        "one_issue_agreement_rate": means[1].to_numpy(),
        "up_to_two_agreement_rate": means[2].to_numpy(),
        "up_to_three_agreement_rate": means[3].to_numpy(),
        "two_vs_one_gain_pp": (100 * (means[2] - means[1])).to_numpy(),
        "three_vs_one_gain_pp": (100 * (means[3] - means[1])).to_numpy(),
    })
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    estimates.to_csv(results / "figure_2_estimates.csv", index=False, float_format="%.8f")
    return means


def plot_results(means):
    fig, (rates, gains) = plt.subplots(1, 2, figsize=(10.8, 4.2), layout="constrained")
    labels = {1: "One issue", 2: "Up to two issues", 3: "Up to three issues"}
    for width, marker in [(1, "o"), (2, "s"), (3, "^")]:
        rates.plot(means.index, 100 * means[width], color=COLORS[width], marker=marker,
                   linewidth=2, label=labels[width])
        if width > 1:
            gains.plot(means.index, 100 * (means[width] - means[1]), color=COLORS[width],
                       marker=marker, linewidth=2, label=labels[width])
    rates.set(title="A. Simulated agreement rates", ylabel="Agreement rate",
              ylim=(0, 105), yticks=[0, 25, 50, 75, 100])
    rates.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    gains.set(title="B. Gain from wider search", ylabel="Gain over one-issue search\n(percentage points)",
              ylim=(0, 70), yticks=[0, 15, 30, 45, 60])
    for axis in (rates, gains):
        axis.set(xlabel="Search complexity", xticks=range(1, 6),
                 xticklabels=["Lowest", "2", "3", "4", "Highest"])
        axis.grid(axis="y", color="#E4E8EC")
        axis.set_axisbelow(True)
        axis.legend(frameon=False, fontsize=9, loc="best")
    save(fig, "figure_2_simulated_agreement")


if __name__ == "__main__":
    illustrate_search()
    plot_results(summarize())
