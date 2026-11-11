"""Adapter from portable metric inputs to the canonical structure table.

Public pipeline interface:

    apply_metric_inputs(structures, sources_dir) -> (structures, audit)

Records without portable calculation inputs use their recorded scores.
Replayed scores must match the recorded scores to numerical tolerance.
An unexpected disagreement stops the build for review.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    from replay_metrics import metrics_from_acceptance
except ModuleNotFoundError:  # supports importlib loading from another directory
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from replay_metrics import metrics_from_acceptance


TOLERANCE = 1e-12


def _replay_row(record, archive) -> dict[str, float | int]:
    shape = tuple(json.loads(record.grid_shape_json))
    bit_count = int(record.offer_count) * int(record.party_count)
    accepts = np.unpackbits(archive[record.archive_key], count=bit_count).reshape(
        int(record.offer_count), int(record.party_count)
    )
    return metrics_from_acceptance(accepts, shape, int(record.required_acceptances))


def apply_metric_inputs(
    structures: pd.DataFrame, sources_dir: str | Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Verify metric calculations and retain recorded scores for other structures.

    Parameters
    ----------
    structures:
        Canonical structure DataFrame. It must contain ``observation_id``,
        ``bargaining_zone_share`` and ``search_complexity``.
    sources_dir:
        Directory containing ``metric_input_manifest.csv`` and
        ``acceptance_inputs.npz``.
    """
    required = {"observation_id", "bargaining_zone_share", "search_complexity"}
    missing = required.difference(structures.columns)
    if missing:
        raise ValueError(f"structures is missing required columns: {sorted(missing)}")
    if not structures.observation_id.is_unique:
        raise ValueError("structures.observation_id must be unique")

    base = Path(sources_dir)
    manifest = pd.read_csv(base / "metric_input_manifest.csv", keep_default_na=False)
    archive = np.load(base / "acceptance_inputs.npz", allow_pickle=False)
    output = structures.copy()
    output_index = output.set_index("observation_id", drop=False)
    audits: list[dict[str, object]] = []
    applied_ids: set[str] = set()

    for record in manifest.itertuples(index=False):
        canonical_id = str(record.canonical_structure_id)
        result = _replay_row(record, archive)
        if not canonical_id:
            audits.append(
                {
                    "observation_id": "",
                    "input_id": record.input_id,
                    "input_status": record.canonical_membership,
                    "recorded_bargaining_zone_share": record.stored_bargaining_zone_share,
                    "replayed_bargaining_zone_share": result["bargaining_zone_share"],
                    "bargaining_zone_difference": (
                        result["bargaining_zone_share"] - float(record.stored_bargaining_zone_share)
                    ),
                    "recorded_search_complexity": record.stored_search_complexity,
                    "replayed_search_complexity": result["search_complexity"],
                    "search_complexity_difference": (
                        result["search_complexity"] - float(record.stored_search_complexity)
                    ),
                    "metric_action": "candidate_not_applied_to_current_structures",
                    "source_locator": record.source_locator,
                }
            )
            continue
        if canonical_id not in output_index.index:
            raise ValueError(f"metric input names absent canonical structure: {canonical_id}")
        if canonical_id in applied_ids:
            raise ValueError(f"more than one metric input maps to {canonical_id}")
        applied_ids.add(canonical_id)
        recorded_bz = float(output_index.at[canonical_id, "bargaining_zone_share"])
        recorded_sc = float(output_index.at[canonical_id, "search_complexity"])
        bz_difference = result["bargaining_zone_share"] - recorded_bz
        sc_difference = result["search_complexity"] - recorded_sc
        agrees = abs(bz_difference) <= TOLERANCE and abs(sc_difference) <= TOLERANCE
        if not agrees:
            raise ValueError(
                f"Recalculated scores differ for {canonical_id}: "
                f"bargaining-zone difference {bz_difference:.12g}, "
                f"search-complexity difference {sc_difference:.12g}. "
                "Run replay_metrics.py to save the calculation audit."
            )
        output_index.at[canonical_id, "bargaining_zone_share"] = result[
            "bargaining_zone_share"
        ]
        output_index.at[canonical_id, "search_complexity"] = result[
            "search_complexity"
        ]
        action = "replayed_value_applied__matches_recorded"
        audits.append(
            {
                "observation_id": canonical_id,
                "input_id": record.input_id,
                "input_status": record.canonical_membership,
                "recorded_bargaining_zone_share": recorded_bz,
                "replayed_bargaining_zone_share": result["bargaining_zone_share"],
                "bargaining_zone_difference": bz_difference,
                "recorded_search_complexity": recorded_sc,
                "replayed_search_complexity": result["search_complexity"],
                "search_complexity_difference": sc_difference,
                "metric_action": action,
                "source_locator": record.source_locator,
            }
        )

    # Make every fallback explicit, including rows with no portable input.
    for row in output_index.itertuples(index=False):
        if row.observation_id in applied_ids:
            continue
        audits.append(
            {
                "observation_id": row.observation_id,
                "input_id": "",
                "input_status": "no_portable_metric_input",
                "recorded_bargaining_zone_share": row.bargaining_zone_share,
                "replayed_bargaining_zone_share": np.nan,
                "bargaining_zone_difference": np.nan,
                "recorded_search_complexity": row.search_complexity,
                "replayed_search_complexity": np.nan,
                "search_complexity_difference": np.nan,
                "metric_action": "recorded_fallback_retained__no_replay_input",
                "source_locator": "",
            }
        )

    return output_index.reset_index(drop=True), pd.DataFrame(audits)
