"""Replay bargaining-zone share and possible-path search complexity.

The portable input contains only derived party-acceptance booleans and the
declared issue grid. It intentionally does not contain copyrighted role text or
full payoff schedules. These two focal metrics depend on acceptance status and
the offer-neighbour graph, so the original payoff magnitudes are not needed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def metrics_from_acceptance(
    accepts: np.ndarray, shape: tuple[int, ...], required_acceptances: int
) -> dict[str, float | int]:
    """Calculate the two focal metrics from an offers-by-parties boolean array."""
    accepts = np.asarray(accepts, dtype=bool)
    offers = int(np.prod(shape, dtype=np.int64))
    if accepts.ndim != 2 or accepts.shape[0] != offers:
        raise ValueError("acceptance array does not match the declared grid")
    if not 1 <= required_acceptances <= accepts.shape[1]:
        raise ValueError("required_acceptances is outside the party count")

    votes = accepts.sum(axis=1).reshape(shape)
    agreement = votes >= required_acceptances
    reachable = agreement.copy()
    # Every valid edge strictly raises the acceptance count. Processing high
    # vote levels first therefore supplies an exact dynamic program.
    for vote_level in range(accepts.shape[1] - 1, -1, -1):
        targets = reachable & (votes > vote_level)
        neighbors_reach = np.zeros(shape, dtype=bool)
        # Reducing an axis asks whether changing only that issue can reach
        # an already reachable offer with more acceptances. Broadcasting
        # evaluates all starting offers sharing the other issue choices.
        for issue_axis in range(len(shape)):
            neighbors_reach |= targets.any(axis=issue_axis, keepdims=True)
        reachable |= (votes == vote_level) & neighbors_reach

    zopa_count = int(agreement.sum())
    return {
        "possible_packages": offers,
        "zopa_count": zopa_count,
        "bargaining_zone_share": float(zopa_count / offers),
        "search_complexity": float(1.0 - reachable.mean()),
    }


def replay(base: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    manifest = pd.read_csv(base / "metric_input_manifest.csv")
    archive = np.load(base / "acceptance_inputs.npz", allow_pickle=False)
    rows: list[dict[str, object]] = []
    for record in manifest.itertuples(index=False):
        shape = tuple(json.loads(record.grid_shape_json))
        packed = archive[record.archive_key]
        bit_count = int(record.offer_count) * int(record.party_count)
        accepts = np.unpackbits(packed, count=bit_count).reshape(
            int(record.offer_count), int(record.party_count)
        )
        result = metrics_from_acceptance(accepts, shape, int(record.required_acceptances))
        bz_difference = result["bargaining_zone_share"] - float(record.stored_bargaining_zone_share)
        sc_difference = result["search_complexity"] - float(record.stored_search_complexity)
        rows.append(
            {
                "input_id": record.input_id,
                "canonical_structure_id": record.canonical_structure_id,
                "canonical_membership": record.canonical_membership,
                "negotiation_scenario": record.negotiation_scenario,
                **result,
                "stored_bargaining_zone_share": record.stored_bargaining_zone_share,
                "stored_search_complexity": record.stored_search_complexity,
                "bargaining_zone_difference": bz_difference,
                "search_complexity_difference": sc_difference,
                "matches_stored_values": bool(
                    abs(bz_difference) <= 1e-12 and abs(sc_difference) <= 1e-12
                ),
            }
        )
    audit = pd.DataFrame(rows)
    summary = {
        "replayed_inputs": int(len(audit)),
        "canonical_structures_replayed": int(
            audit.loc[
                audit.canonical_membership.str.startswith("current_104_structure_file"),
                "canonical_structure_id",
            ].nunique()
        ),
        "verified_candidates_replayed": int(
            (~audit.canonical_membership.str.startswith("current_104_structure_file")).sum()
        ),
        "matching_inputs": int(audit.matches_stored_values.sum()),
        "disagreements": int((~audit.matches_stored_values).sum()),
        "maximum_absolute_bargaining_zone_difference": float(
            audit.bargaining_zone_difference.abs().max()
        ),
        "maximum_absolute_search_complexity_difference": float(
            audit.search_complexity_difference.abs().max()
        ),
        "disagreement_input_ids": audit.loc[
            ~audit.matches_stored_values, "input_id"
        ].tolist(),
    }
    return audit, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parent
    parser.add_argument("--base", type=Path, default=root / "data" / "sources")
    parser.add_argument("--output", type=Path, default=root / "outputs")
    args = parser.parse_args()
    audit, summary = replay(args.base)
    args.output.mkdir(parents=True, exist_ok=True)
    audit.to_csv(args.output / "metric_replay_audit.csv", index=False, encoding="utf-8-sig")
    (args.output / "metric_replay_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if summary["disagreements"]:
        raise SystemExit("Recalculated scores differ from recorded scores. Review the saved audit.")


if __name__ == "__main__":
    main()
