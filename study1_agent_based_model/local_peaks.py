"""Check whether the simulation results hold when complexity counts local peaks."""

import gzip
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from scripts.supporting.payoff_metrics import local_peak_mask


def calculate(parties):
    suffix = "_two_party" if parties == 2 else ""
    runs = pd.read_csv(ROOT / "data" / f"simulation_conditions{suffix}.csv")
    with gzip.open(ROOT / "data" / f"negotiations{suffix}.json.gz", "rt",
                   encoding="utf-8") as source:
        scenarios = json.load(source)
    counts = {}
    for index, scenario in scenarios.items():
        issue_tables = [np.asarray(table, dtype=float) for table in scenario["issue_payoffs"]]
        shape = tuple(len(table) for table in issue_tables)
        coordinates = np.indices(shape).reshape(len(shape), -1)
        totals = sum(table[coordinates[i]] for i, table in enumerate(issue_tables))
        votes = (totals >= scenario["reservations"]).sum(axis=1).reshape(shape)
        acceptable = votes == parties
        counts[int(index)] = (int(local_peak_mask(votes, acceptable).sum()), int(acceptable.sum()))
    peaks = pd.DataFrame.from_dict(counts, orient="index", columns=["local_peak_count", "zone_check"])
    data = runs.join(peaks, on="scenario_index", validate="many_to_one")
    if not data.zone_check.eq(data.zopa_count).all():
        raise ValueError("Recomputed agreement counts differ from the saved structures.")

    rates = data.pivot(index="scenario_index", columns="search_distance", values="agreement_rate")
    rates = rates.rename(columns={1: "one_issue", 2: "up_to_two_issues", 3: "up_to_three_issues"})
    rates = rates.join(peaks["local_peak_count"])
    rates["gain_two_vs_one"] = rates.up_to_two_issues - rates.one_issue
    rates["gain_three_vs_one"] = rates.up_to_three_issues - rates.one_issue
    return rates.assign(parties=parties).reset_index()


def main():
    frames = [calculate(parties) for parties in (6, 2)]
    counts = pd.concat(frames, ignore_index=True)
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    counts.to_csv(output / "local_peak_counts.csv", index=False, float_format="%.8f")

    comparisons = []
    bins = []
    terms = ["one_issue", "up_to_two_issues", "up_to_three_issues",
             "gain_two_vs_one", "gain_three_vs_one"]
    for parties, group in counts.groupby("parties", sort=False):
        for term in terms:
            rho, p = spearmanr(group.local_peak_count, group[term])
            comparisons.append({"parties": parties, "outcome": term, "structures": len(group),
                                "spearman_rho": rho, "p": p})

        # Use count ranges shared by both group sizes. An empty range is omitted.
        intervals = pd.cut(group.local_peak_count, [-1, 0, 25, 50, 100, 200, 1024],
                           labels=["0", "1–25", "26–50", "51–100", "101–200", "201–1024"])
        for span, data in group.groupby(intervals, observed=True):
            bins.append({"parties": parties, "local_peak_count_bin": span,
                         "structures": len(data), **data[terms].mean().to_dict()})
    pd.DataFrame(comparisons).to_csv(output / "local_peak_correlations.csv", index=False)
    summary = pd.DataFrame(bins)
    summary.to_csv(output / "local_peak_agreement_rates.csv", index=False, float_format="%.8f")
    print(pd.DataFrame(comparisons).to_string(index=False))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
