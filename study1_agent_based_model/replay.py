"""Replay the saved model on one or more of the generated negotiations."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from supporting import negotiation_search_engine as model


ROOT = Path(__file__).resolve().parent
BASE_SEED = 20260818


def replay(scenario_count, output):
    saved = pd.read_csv(ROOT / "data" / "simulation_conditions.csv")
    with gzip.open(ROOT / "data" / "negotiations.json.gz", "rt", encoding="utf-8") as source:
        scenarios = json.load(source)
    if not 1 <= scenario_count <= len(scenarios):
        raise ValueError(f"Choose between 1 and {len(scenarios)} negotiations.")

    rows = []
    for index, group in list(saved.groupby("scenario_index"))[:scenario_count]:
        scenario = model.scenario_from_dict(scenarios[str(index)])
        prepared = model.prepare_scenario(scenario, weak_acceptance=True, max_search_distance=3)
        metrics = model.scenario_metrics(prepared)
        for row in group.to_dict(orient="records"):
            seeds = range(BASE_SEED + int(index) * 100_000 + 6_000,
                          BASE_SEED + int(index) * 100_000 + 6_000 + row["n_runs"])
            agreements = sum(
                model.simulate_once(
                    prepared, alpha=.5, seed=seed, first_offer_rule="ambitious",
                    ambitious_top_k=3, reference_rule=1, search_distance=row["search_distance"],
                    agreement_stopping_rule="first_consensus",
                )["agreement"]
                for seed in seeds
            )
            rate = agreements / row["n_runs"]
            np.testing.assert_allclose(
                [rate, metrics["ruggedness_possible_path"], metrics["zopa_share"]],
                [row["agreement_rate"], row["search_complexity"], row["zopa_share"]],
                rtol=0, atol=1e-12,
                err_msg=f"Saved and replayed values differ for {row['scenario_id']} "
                        f"with a maximum change of {row['search_distance']} issues.",
            )
            if metrics["zopa_count"] != row["zopa_count"]:
                raise ValueError(f"Bargaining-zone counts differ for {row['scenario_id']}.")
            rows.append({**row, "agreement_rate": rate})
        print(f"Matched all three search conditions for {scenario.scenario_id}.", flush=True)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Reproduced {len(rows)} saved agreement rates and structural checks.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=int, default=1,
                        help="Number of negotiations to replay, starting at the first saved index.")
    parser.add_argument("--output", type=Path, help="Optional path for the replayed conditions CSV.")
    args = parser.parse_args()
    replay(args.scenarios, args.output)
