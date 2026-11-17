"""Lean negotiation-as-search simulation.

The engine implements the behavioral rules stated in the paper's Model section
without materializing an offer-to-offer transition table.  Offers, payoffs,
acceptance counts, and local neighbor lists are precomputed once per scenario.

Key behavioral rule
-------------------
On every counteroffer, alpha is a Bernoulli probability:

* with probability ``alpha``, use the complete group offer history;
* with probability ``1 - alpha``, use only the proposer's own history.

Within the selected history, the reference is the offer accepted by the most
parties, with recency breaking ties.  The implementation keeps only the current
best reference for each scope; this is an exact sufficient statistic for the
full-history rule, not the anchor-promotion approximation used in the older
Step 2 notebook.

After the reference offer is selected, the proposer enumerates every eligible
offer within maximum Hamming distance D, ranks those offers by the proposer's
own payoff, and proposes the highest-ranked offer that is not forbidden by the
selected history scope. This payoff ranking is the model's counteroffer rule.

Agreement and settlement
------------------------
The main stopping setting is satisficing: the run ends at the first mutually
acceptable offer. The optimizing comparison continues until the same
search-exhaustion condition used for impasse, then settles on the discovered
acceptable offer with the highest joint payoff; recency breaks exact ties.

Pareto efficiency is evaluated against every mutually acceptable offer in the
full bargaining zone.  It is an outcome, not a settlement constraint.  The
engine reports both a nondominance indicator and the agreement's joint payoff
as a share of the maximum joint payoff available anywhere in the bargaining
zone.

Randomness and reproducibility
------------------------------
Candidate ranking is deterministic conditional on the current state.  A run
remains stochastic because the opening party/offer, the active proposer on
each turn, and (when 0 < alpha < 1) the history-scope draw are seeded.  Study
runners deliberately reuse the same run seeds across alpha, D, first-offer,
and reference-rule conditions to implement common-random-number comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
import json
import math
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass
class NegotiationScenario:
    """Issue-level payoffs for a negotiation scenario.

    ``issue_payoffs[j]`` has shape ``(options_on_issue_j, parties)``.  An offer
    is a tuple of zero-based option indices, one index per issue.  This ragged
    representation supports both the paper's binary random landscapes and
    canonical scenarios with more than two options on an issue.
    """

    scenario_id: str
    party_names: tuple[str, ...]
    issue_names: tuple[str, ...]
    option_labels: tuple[tuple[str, ...], ...]
    issue_payoffs: tuple[np.ndarray, ...]
    reservations: np.ndarray

    def __post_init__(self) -> None:
        n = len(self.party_names)
        if len(self.issue_names) != len(self.option_labels):
            raise ValueError("Each issue must have a corresponding option-label list.")
        if len(self.issue_names) != len(self.issue_payoffs):
            raise ValueError("Each issue must have a corresponding payoff array.")
        if np.asarray(self.reservations).shape != (n,):
            raise ValueError("reservations must have one value per party.")
        for labels, payoffs in zip(self.option_labels, self.issue_payoffs):
            if np.asarray(payoffs).shape != (len(labels), n):
                raise ValueError("Every issue payoff array must be options x parties.")

    @property
    def n_parties(self) -> int:
        return len(self.party_names)

    @property
    def n_issues(self) -> int:
        return len(self.issue_names)

    def subset_parties(self, n_parties: int) -> "NegotiationScenario":
        """Return the first ``n_parties`` for a paired group-size design."""
        if not 1 <= n_parties <= self.n_parties:
            raise ValueError("n_parties must be between 1 and the scenario party count.")
        return NegotiationScenario(
            scenario_id=f"{self.scenario_id}_N={n_parties}",
            party_names=self.party_names[:n_parties],
            issue_names=self.issue_names,
            option_labels=self.option_labels,
            issue_payoffs=tuple(np.asarray(p)[:, :n_parties].copy() for p in self.issue_payoffs),
            reservations=np.asarray(self.reservations[:n_parties], dtype=float).copy(),
        )

    def subset_issues(self, n_issues: int) -> "NegotiationScenario":
        """Return an issue-prefix landscape for a paired comparison across M."""
        if not 1 <= n_issues <= self.n_issues:
            raise ValueError("n_issues must be between 1 and the scenario issue count.")
        return NegotiationScenario(
            scenario_id=f"{self.scenario_id}_M={n_issues}",
            party_names=self.party_names,
            issue_names=self.issue_names[:n_issues],
            option_labels=self.option_labels[:n_issues],
            issue_payoffs=tuple(np.asarray(p).copy() for p in self.issue_payoffs[:n_issues]),
            reservations=np.asarray(self.reservations, dtype=float).copy(),
        )


@dataclass
class PreparedScenario:
    """Scenario arrays reused across simulation runs and alpha conditions."""

    scenario: NegotiationScenario
    offers: np.ndarray
    payoffs: np.ndarray
    accepts: np.ndarray
    votes: np.ndarray
    consensus: np.ndarray
    pareto_efficient_consensus: np.ndarray
    best_consensus_joint_payoff: float
    neighbors: Sequence[np.ndarray]
    eligible_neighbors: tuple[Sequence[np.ndarray], ...]
    neighbors_by_distance: tuple[Sequence[np.ndarray], ...]
    eligible_neighbors_by_distance: tuple[tuple[Sequence[np.ndarray], ...], ...]
    ambitious_starts: tuple[np.ndarray, ...]
    ambitious_rankings: tuple[np.ndarray, ...]
    feasible_starts: tuple[np.ndarray, ...]

    @property
    def n_offers(self) -> int:
        return int(self.offers.shape[0])


@dataclass
class PreparedExperimentCase:
    """One base-scenario × group-size structure ready for repeated runs."""

    base_scenario_id: str
    prepared: PreparedScenario
    metrics: dict[str, float | int | str]


def generate_random_base_scenarios(
    count: int = 20,
    *,
    n_parties: int = 6,
    n_issues: int = 7,
    seed: int = 20260818,
    decimals: int | None = 2,
) -> list[NegotiationScenario]:
    """Generate binary additive scenarios using the Step 1 payoff convention.

    Excluding an issue gives zero; including it gives a U[-1, 1] payoff.
    Reservation values are zero and acceptance is weak (payoff >= reservation),
    matching the notebooks' ``Accepting`` rule.
    """
    rng = np.random.default_rng(seed)
    scenarios: list[NegotiationScenario] = []
    for s in range(count):
        draws = rng.uniform(-1.0, 1.0, size=(n_issues, n_parties))
        if decimals is not None:
            draws = np.round(draws, decimals)
        issue_payoffs = tuple(
            np.vstack([np.zeros(n_parties, dtype=float), draws[j].astype(float)])
            for j in range(n_issues)
        )
        scenarios.append(
            NegotiationScenario(
                scenario_id=f"random_{s + 1:02d}",
                party_names=tuple(f"P{i + 1}" for i in range(n_parties)),
                issue_names=tuple(f"Issue_{j + 1}" for j in range(n_issues)),
                option_labels=tuple(("off", "on") for _ in range(n_issues)),
                issue_payoffs=issue_payoffs,
                reservations=np.zeros(n_parties, dtype=float),
            )
        )
    return scenarios


def load_scenario_frame(
    frame: pd.DataFrame, *, scenario_id: str = "manual_scenario"
) -> NegotiationScenario:
    """Validate and load a Step 1-style scenario table.

    The first two named fields must be ``issue`` and ``option`` (case and
    surrounding spaces are ignored); every remaining field is one party's
    payoff.  ``reservation``/``reservation price`` and ``target``/``target
    price`` rows are metadata rather than negotiable issues.  Missing or
    non-numeric payoffs in a real issue are rejected instead of silently being
    changed to zero.
    """
    df = frame.copy()
    df.columns = [str(column).strip() for column in df.columns]
    lowered = {str(c).strip().casefold(): c for c in df.columns}
    issue_col = lowered.get("issue")
    option_col = lowered.get("option")
    if issue_col is None or option_col is None:
        raise ValueError("Scenario CSV needs 'issue' and 'option' columns.")

    party_cols = [c for c in df.columns if c not in {issue_col, option_col}]
    if not party_cols:
        raise ValueError("Scenario CSV has no party payoff columns.")
    if len(set(str(column).strip().casefold() for column in party_cols)) != len(party_cols):
        raise ValueError("Scenario CSV has duplicate party names after spaces are removed.")
    for col in party_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    issue_key = df[issue_col].astype(str).str.strip().str.casefold()
    reservation_mask = issue_key.isin({"reservation", "reservation price"})
    target_mask = issue_key.isin({"target", "target price"})
    reservation_rows = df.loc[reservation_mask, party_cols]
    if len(reservation_rows) > 1:
        raise ValueError("Scenario CSV has more than one reservation row.")
    if not reservation_rows.empty and reservation_rows.iloc[0].isna().any():
        missing = [str(column) for column in party_cols if pd.isna(reservation_rows.iloc[0][column])]
        raise ValueError("Reservation row has missing/non-numeric values for: " + ", ".join(missing))
    reservations = (
        reservation_rows.iloc[0].to_numpy(dtype=float)
        if not reservation_rows.empty
        else np.zeros(len(party_cols), dtype=float)
    )
    core = df.loc[~(reservation_mask | target_mask)].copy()
    if core.empty:
        raise ValueError("Scenario CSV contains no issue-option rows.")
    if core[issue_col].isna().any() or core[issue_col].astype(str).str.strip().eq("").any():
        raise ValueError("Every negotiable row needs an issue name.")
    if core[option_col].isna().any() or core[option_col].astype(str).str.strip().eq("").any():
        raise ValueError("Every negotiable row needs an option label.")
    bad_payoffs = core[party_cols].isna()
    if bad_payoffs.any().any():
        locations = []
        for row_index, column in zip(*np.where(bad_payoffs.to_numpy())):
            locations.append(f"row {int(core.index[row_index]) + 2}, {party_cols[int(column)]}")
            if len(locations) == 5:
                break
        raise ValueError(
            "Issue-option payoffs must all be numeric. Check " + "; ".join(locations) + "."
        )

    issue_names: list[str] = []
    option_labels: list[tuple[str, ...]] = []
    issue_payoffs: list[np.ndarray] = []
    for issue_value in core[issue_col].drop_duplicates().tolist():
        block = core.loc[core[issue_col].eq(issue_value)].copy()
        labels = tuple(block[option_col].astype(str).str.strip().tolist())
        if len(labels) < 2:
            raise ValueError(f"Issue {issue_value!r} has fewer than two options.")
        if len(set(labels)) != len(labels):
            raise ValueError(f"Issue {issue_value!r} has duplicate option labels.")
        issue_names.append(str(issue_value).strip())
        option_labels.append(labels)
        issue_payoffs.append(block[party_cols].to_numpy(dtype=float))

    return NegotiationScenario(
        scenario_id=str(scenario_id),
        party_names=tuple(str(column).strip() for column in party_cols),
        issue_names=tuple(issue_names),
        option_labels=tuple(option_labels),
        issue_payoffs=tuple(issue_payoffs),
        reservations=reservations,
    )


def load_scenario_csv(path: str | Path) -> NegotiationScenario:
    """Load a validated manual scenario from a CSV file."""
    path = Path(path)
    return load_scenario_frame(pd.read_csv(path), scenario_id=path.stem)


def _neighbor_indices_at_distance(
    offers: np.ndarray,
    option_counts: Sequence[int],
    distance: int,
) -> tuple[np.ndarray, ...]:
    """Enumerate offers within a maximum Hamming distance, excluding self.

    Thus D=1 changes one issue; D=2 may change one or two issues; and D=3
    may change one, two, or three issues.  No S x S transition matrix is built.
    """
    distance = int(distance)
    if not 1 <= distance <= len(option_counts):
        raise ValueError("distance must be between 1 and the number of issues.")
    offer_to_idx = {tuple(map(int, offer)): i for i, offer in enumerate(offers)}
    result: list[np.ndarray] = []
    for offer in offers:
        local: list[int] = []
        for changed_count in range(1, distance + 1):
            for changed_issues in combinations(range(len(option_counts)), changed_count):
                alternatives = [
                    [x for x in range(option_counts[issue]) if x != int(offer[issue])]
                    for issue in changed_issues
                ]
                for replacement_values in product(*alternatives):
                    candidate = offer.copy()
                    for issue, alternative in zip(changed_issues, replacement_values):
                        candidate[issue] = alternative
                    local.append(offer_to_idx[tuple(map(int, candidate))])
        result.append(np.asarray(local, dtype=np.int32))
    return tuple(result)


class _LazyNeighbors(Sequence[np.ndarray]):
    """Exact Hamming neighborhoods computed only when a large landscape visits them."""

    def __init__(self, offers: np.ndarray, option_counts: Sequence[int], distance: int):
        self.offers = offers
        self.option_counts = tuple(map(int, option_counts))
        self.distance = int(distance)
        self.strides = np.asarray(
            [math.prod(self.option_counts[index + 1:]) for index in range(len(self.option_counts))],
            dtype=np.int64,
        )

    def __len__(self) -> int:
        return len(self.offers)

    def __getitem__(self, index: int | slice) -> np.ndarray | list[np.ndarray]:
        if isinstance(index, slice):
            return [self[item] for item in range(*index.indices(len(self)))]
        offer = self.offers[int(index)]
        local: list[int] = []
        for changed_count in range(1, self.distance + 1):
            for changed_issues in combinations(range(len(self.option_counts)), changed_count):
                alternatives = [
                    [value for value in range(self.option_counts[issue]) if value != int(offer[issue])]
                    for issue in changed_issues
                ]
                for replacements in product(*alternatives):
                    candidate_index = int(index)
                    for issue, replacement in zip(changed_issues, replacements):
                        candidate_index += int(replacement - int(offer[issue])) * int(self.strides[issue])
                    local.append(candidate_index)
        return np.asarray(local, dtype=np.int32)


class _LazyEligibleNeighbors(Sequence[np.ndarray]):
    def __init__(
        self,
        neighbors: Sequence[np.ndarray],
        accepted: np.ndarray,
        proposer_payoffs: np.ndarray | None = None,
    ):
        self.neighbors = neighbors
        self.accepted = np.asarray(accepted, dtype=bool)
        self.proposer_payoffs = (
            None if proposer_payoffs is None else np.asarray(proposer_payoffs, dtype=float)
        )
        self._cache: dict[int, np.ndarray] = {}

    def __len__(self) -> int:
        return len(self.neighbors)

    def __getitem__(self, index: int | slice) -> np.ndarray | list[np.ndarray]:
        if isinstance(index, slice):
            return [self[item] for item in range(*index.indices(len(self)))]
        index = int(index)
        if index in self._cache:
            return self._cache[index]
        local = np.asarray(self.neighbors[index], dtype=np.int32)
        local = local[self.accepted[local]]
        if self.proposer_payoffs is not None and local.size > 1:
            local = local[
                np.lexsort((local, -self.proposer_payoffs[local]))
            ]
        self._cache[index] = local
        return local


def _ranked_eligible_neighbors(
    local: np.ndarray,
    proposer_payoffs: np.ndarray,
) -> np.ndarray:
    """Sort once by proposer payoff, then stable offer index.

    ``simulate_once`` still applies the original ``np.isclose`` tie rule when
    it chooses from this list, so matched seeds produce the same offer history.
    """
    local = np.asarray(local, dtype=np.int32)
    if local.size <= 1:
        return local
    return local[np.lexsort((local, -np.asarray(proposer_payoffs)[local]))]


def _neighbor_indices(offers: np.ndarray, option_counts: Sequence[int]) -> tuple[np.ndarray, ...]:
    """Backward-compatible one-issue-neighbor helper."""
    return _neighbor_indices_at_distance(offers, option_counts, 1)


def prepare_scenario(
    scenario: NegotiationScenario,
    *,
    ambitious_top_k: int = 3,
    weak_acceptance: bool = True,
    max_search_distance: int = 1,
) -> PreparedScenario:
    """Enumerate offers once and precompute all quantities used by the engine."""
    option_counts = [len(options) for options in scenario.option_labels]
    offers = np.asarray(list(product(*(range(k) for k in option_counts))), dtype=np.int16)
    payoffs = np.zeros((len(offers), scenario.n_parties), dtype=float)
    for issue, contribution in enumerate(scenario.issue_payoffs):
        payoffs += np.asarray(contribution, dtype=float)[offers[:, issue]]

    reservations = np.asarray(scenario.reservations, dtype=float)
    accepts = payoffs >= reservations if weak_acceptance else payoffs > reservations
    votes = accepts.sum(axis=1).astype(np.int16)
    consensus = votes.eq(scenario.n_parties) if isinstance(votes, pd.Series) else votes == scenario.n_parties
    consensus = np.asarray(consensus, dtype=bool)
    pareto_efficient_consensus = np.zeros(len(offers), dtype=bool)
    consensus_indices = np.flatnonzero(consensus)
    if consensus_indices.size:
        zopa_payoffs = payoffs[consensus_indices]
        for local_index, offer_index in enumerate(consensus_indices):
            candidate = zopa_payoffs[local_index]
            weakly_better = np.all(zopa_payoffs >= candidate - 1e-12, axis=1)
            strictly_better = np.any(zopa_payoffs > candidate + 1e-12, axis=1)
            pareto_efficient_consensus[int(offer_index)] = not bool(
                np.any(weakly_better & strictly_better)
            )
        best_consensus_joint_payoff = float(zopa_payoffs.sum(axis=1).max())
    else:
        best_consensus_joint_payoff = np.nan
    max_search_distance = int(max_search_distance)
    if not 1 <= max_search_distance <= scenario.n_issues:
        raise ValueError("max_search_distance must be between 1 and M.")
    references_per_offer = []
    for distance in range(1, max_search_distance + 1):
        count = 0
        for changed_count in range(1, distance + 1):
            for changed_issues in combinations(range(len(option_counts)), changed_count):
                count += math.prod(option_counts[issue] - 1 for issue in changed_issues)
        references_per_offer.append(count)
    neighbors_by_distance = tuple(
        _neighbor_indices_at_distance(offers, option_counts, distance)
        if len(offers) * references_per_offer[distance - 1] <= 5_000_000
        else _LazyNeighbors(offers, option_counts, distance)
        for distance in range(1, max_search_distance + 1)
    )
    neighbors = neighbors_by_distance[0]

    eligible_by_distance: list[tuple[tuple[np.ndarray, ...], ...]] = []
    for distance_neighbors in neighbors_by_distance:
        eligible_for_distance: list[tuple[np.ndarray, ...]] = []
        for party in range(scenario.n_parties):
            if isinstance(distance_neighbors, _LazyNeighbors):
                eligible_for_distance.append(
                    _LazyEligibleNeighbors(
                        distance_neighbors,
                        accepts[:, party],
                        payoffs[:, party],
                    )
                )
            else:
                eligible_for_distance.append(
                    tuple(
                        _ranked_eligible_neighbors(
                            local[accepts[local, party]],
                            payoffs[:, party],
                        )
                        for local in distance_neighbors
                    )
                )
        eligible_by_distance.append(tuple(eligible_for_distance))
    eligible = eligible_by_distance[0]

    starts: list[np.ndarray] = []
    rankings: list[np.ndarray] = []
    feasible_starts: list[np.ndarray] = []
    for party in range(scenario.n_parties):
        feasible = np.flatnonzero(accepts[:, party])
        feasible_starts.append(feasible.astype(np.int32))
        if feasible.size == 0:
            starts.append(np.asarray([], dtype=np.int32))
            rankings.append(np.asarray([], dtype=np.int32))
        else:
            ordered = feasible[np.argsort(-payoffs[feasible, party], kind="stable")]
            rankings.append(ordered.astype(np.int32))
            starts.append(ordered[: min(ambitious_top_k, ordered.size)].astype(np.int32))

    return PreparedScenario(
        scenario=scenario,
        offers=offers,
        payoffs=payoffs,
        accepts=accepts,
        votes=votes,
        consensus=consensus,
        pareto_efficient_consensus=pareto_efficient_consensus,
        best_consensus_joint_payoff=best_consensus_joint_payoff,
        neighbors=neighbors,
        eligible_neighbors=eligible,
        neighbors_by_distance=neighbors_by_distance,
        eligible_neighbors_by_distance=tuple(eligible_by_distance),
        ambitious_starts=tuple(starts),
        ambitious_rankings=tuple(rankings),
        feasible_starts=tuple(feasible_starts),
    )


def ruggedness_possible_path(prepared: PreparedScenario) -> float:
    """Primary metric: share of starts with no vote-improving path to the ZOPA.

    An edge exists from an offer to each Hamming-distance-one neighbor accepted
    by strictly more parties. A start is reachable when at least one such path
    ends in the bargaining zone. Because votes strictly rise along every edge,
    reachability can be solved by dynamic programming over vote levels.
    """
    reachable = prepared.consensus.copy()
    for vote_level in range(prepared.scenario.n_parties - 1, -1, -1):
        for node in np.flatnonzero(prepared.votes == vote_level):
            local = prepared.neighbors[int(node)]
            improving = local[prepared.votes[local] > vote_level]
            if improving.size and bool(np.any(reachable[improving])):
                reachable[int(node)] = True
    return float(1.0 - reachable.mean())


def scenario_metrics(prepared: PreparedScenario) -> dict[str, float | int | str]:
    """Structural quantities used in the analysis."""
    zopa = int(prepared.consensus.sum())
    possible_path = ruggedness_possible_path(prepared)
    return {
        "scenario_id": prepared.scenario.scenario_id,
        "N": prepared.scenario.n_parties,
        "M": prepared.scenario.n_issues,
        "possible_offers": prepared.n_offers,
        "zopa_count": zopa,
        "zopa_share": zopa / prepared.n_offers,
        "ruggedness": possible_path,
        "ruggedness_possible_path": possible_path,
    }


def simulate_once(
    prepared: PreparedScenario,
    *,
    alpha: float,
    seed: int,
    max_offers: int | None = None,
    first_offer_rule: str = "ambitious",
    ambitious_top_k: int = 3,
    reference_rule: int = 1,
    search_distance: int = 1,
    agreement_stopping_rule: str = "first_consensus",
) -> dict[str, object]:
    """Simulate one negotiation under the paper-defined behavioral rules.

    ``first_offer_rule`` is ``"ambitious"`` (randomly draw from the proposer's
    ``ambitious_top_k`` highest-payoff feasible offers) or ``"random"`` (draw
    from all feasible offers).  The paper's baseline is ``ambitious_top_k=3``.

    ``reference_rule`` implements Table 1 in the paper without a transition
    matrix: R1 maximizes acceptances and breaks ties by recency; R2 additionally
    breaks acceptance ties by proposer payoff; R3 uses the most recent offer in
    the union of the acceptance-maximizing and proposer-payoff-maximizing sets.

    Counteroffers use the model's payoff-ranked search rule. The proposer ranks
    all currently eligible, unoffered offers within maximum Hamming distance D
    by own payoff and selects the highest-ranked one. Because forbidden offers
    are excluded on later turns, an unchanged proposer/reference/scope exhausts
    its D-neighborhood in descending proposer-payoff order.

    ``agreement_stopping_rule="first_consensus"`` is the model default: the
    negotiation stops when the first mutually acceptable offer is found.  This
    is the satisficing rule.  ``"exhaustive"`` is the optimizing comparison:
    it records the first viable offer, continues until all proposers are
    inactive or the safety limit is reached, and settles on the discovered
    consensus offer with the largest joint payoff (recency breaks exact ties).
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1].")
    rule_name = str(first_offer_rule).strip().lower().replace("-", "_")
    if rule_name in {"top_value", "top", "egoistic"}:
        rule_name = "ambitious"
    if rule_name not in {"ambitious", "random"}:
        raise ValueError("first_offer_rule must be 'ambitious' or 'random'.")
    ambitious_top_k = int(ambitious_top_k)
    if ambitious_top_k < 1:
        raise ValueError("ambitious_top_k (A) must be at least 1.")
    if int(reference_rule) not in {1, 2, 3}:
        raise ValueError("reference_rule must be 1, 2, or 3.")
    reference_rule = int(reference_rule)
    stop_rule = str(agreement_stopping_rule).strip().lower().replace("-", "_")
    if stop_rule in {"first", "agreement", "immediate", "first_agreement"}:
        stop_rule = "first_consensus"
    if stop_rule in {"continue", "continue_to_exhaustion", "post_agreement"}:
        stop_rule = "exhaustive"
    if stop_rule not in {"exhaustive", "first_consensus"}:
        raise ValueError("agreement_stopping_rule must be 'exhaustive' or 'first_consensus'.")
    search_distance = int(search_distance)
    if not 1 <= search_distance <= len(prepared.eligible_neighbors_by_distance):
        raise ValueError(
            "search_distance was not precomputed; call prepare_scenario(..., "
            "max_search_distance=search_distance)."
        )
    rng = np.random.default_rng(seed)
    n_parties = prepared.scenario.n_parties
    active = np.ones(n_parties, dtype=bool)
    offered_global: set[int] = set()
    offered_self: list[set[int]] = [set() for _ in range(n_parties)]
    own_vote_reference: list[int | None] = [None] * n_parties
    own_competitive_reference: list[int | None] = [None] * n_parties
    own_payoff_reference: list[int | None] = [None] * n_parties
    social_vote_reference: int | None = None
    social_competitive_reference: list[int | None] = [None] * n_parties
    social_payoff_reference: list[int | None] = [None] * n_parties
    last_occurrence: dict[int, int] = {}
    history: list[int] = []
    proposers: list[int] = []
    scopes: list[str] = []

    def register(party: int, offer: int, scope: str) -> None:
        nonlocal social_vote_reference
        offer = int(offer)
        history.append(offer)
        proposers.append(int(party))
        scopes.append(scope)
        last_occurrence[offer] = len(history) - 1
        offered_global.add(offer)
        offered_self[party].add(offer)

        current = own_vote_reference[party]
        if current is None or prepared.votes[offer] >= prepared.votes[current]:
            own_vote_reference[party] = offer
        current = social_vote_reference
        if current is None or prepared.votes[offer] >= prepared.votes[current]:
            social_vote_reference = offer

        current = own_competitive_reference[party]
        if current is None or (
            int(prepared.votes[offer]), float(prepared.payoffs[offer, party])
        ) >= (
            int(prepared.votes[current]), float(prepared.payoffs[current, party])
        ):
            own_competitive_reference[party] = offer

        current = own_payoff_reference[party]
        if current is None or prepared.payoffs[offer, party] >= prepared.payoffs[current, party]:
            own_payoff_reference[party] = offer

        # Social histories are common, but R2/R3 evaluate own payoff from the
        # perspective of the party whose turn it is.  Keep one sufficient
        # statistic per possible proposer rather than rescanning the history.
        for evaluator in range(n_parties):
            current = social_competitive_reference[evaluator]
            if current is None or (
                int(prepared.votes[offer]), float(prepared.payoffs[offer, evaluator])
            ) >= (
                int(prepared.votes[current]), float(prepared.payoffs[current, evaluator])
            ):
                social_competitive_reference[evaluator] = offer
            current = social_payoff_reference[evaluator]
            if current is None or prepared.payoffs[offer, evaluator] >= prepared.payoffs[current, evaluator]:
                social_payoff_reference[evaluator] = offer

    def choose_reference(party: int, use_social: bool) -> int | None:
        if reference_rule == 1:
            return social_vote_reference if use_social else own_vote_reference[party]
        if reference_rule == 2:
            return social_competitive_reference[party] if use_social else own_competitive_reference[party]
        vote_ref = social_vote_reference if use_social else own_vote_reference[party]
        payoff_ref = social_payoff_reference[party] if use_social else own_payoff_reference[party]
        if vote_ref is None:
            return payoff_ref
        if payoff_ref is None:
            return vote_ref
        return payoff_ref if last_occurrence[payoff_ref] >= last_occurrence[vote_ref] else vote_ref

    def start_options(party: int, forbidden: set[int]) -> list[int]:
        source = (
            prepared.ambitious_rankings[party][
                : min(ambitious_top_k, prepared.ambitious_rankings[party].size)
            ]
            if rule_name == "ambitious"
            else prepared.feasible_starts[party]
        )
        return [int(x) for x in source if int(x) not in forbidden]

    first_party = int(rng.integers(n_parties))
    first_options = start_options(first_party, set())
    if not first_options:
        return {
            "agreement": 0,
            "agreement_step": np.nan,
            "offers": 0,
            "termination": "no_first_offer",
            "first_party": first_party,
            "final_offer": None,
            "settlement_offer": None,
            "mean_payoff": 0.0,
            "first_offer_rule": rule_name,
            "ambitious_top_k": ambitious_top_k,
            "reference_rule": reference_rule,
            "search_distance": search_distance,
            "local_search_rule": "proposer_ranked",
            "agreement_stopping_rule": stop_rule,
            "first_consensus_offer": None,
            "first_offer": None,
            "first_offer_proposer": None,
            "first_offer_scope": None,
            "first_consensus_proposer": None,
            "first_consensus_scope": None,
            "last_offer_proposer": None,
            "last_offer_scope": None,
            "settlement_offer_proposer": None,
            "settlement_offer_scope": None,
            "first_consensus_step": np.nan,
            "offers_to_first_consensus": np.nan,
            "post_consensus_offers": 0,
            "first_consensus_mean_payoff": np.nan,
            "first_consensus_joint_payoff": np.nan,
            "settlement_mean_payoff": 0.0,
            "settlement_joint_payoff": 0.0,
            "settlement_gain_mean_payoff": np.nan,
            "first_consensus_pareto_efficient": np.nan,
            "settlement_pareto_efficient": np.nan,
            "first_consensus_joint_payoff_ratio": np.nan,
            "settlement_joint_payoff_ratio": np.nan,
            "last_offer": None,
            "history": [],
            "proposers": [],
            "scopes": [],
        }
    first_offer = int(rng.choice(first_options))
    register(first_party, first_offer, "first")
    agreement = bool(prepared.consensus[first_offer])
    consensus_offers: set[int] = {first_offer} if agreement else set()
    first_consensus_offer: int | None = first_offer if agreement else None
    first_consensus_step: int | None = 1 if agreement else None
    termination = "agreement" if agreement and stop_rule == "first_consensus" else ""

    safety_limit = max_offers if max_offers is not None else n_parties * prepared.n_offers
    while (
        not (agreement and stop_rule == "first_consensus")
        and bool(active.any())
        and len(history) < safety_limit
    ):
        party = int(rng.choice(np.flatnonzero(active)))
        use_social = bool(rng.random() < alpha)
        scope = "social" if use_social else "self"
        reference = choose_reference(party, use_social)

        if reference is None:
            # The selected own history is empty: this party originates an
            # ambitious offer. Under self-directed search, others' offers do
            # not count as repetitions (paper Model section, paragraph 73).
            starts = start_options(party, offered_self[party])
            if not starts:
                active[party] = False
                continue
            candidate = int(rng.choice(starts))
            register(party, candidate, "own_first")
        else:
            forbidden = offered_global if use_social else offered_self[party]
            ranked = prepared.eligible_neighbors_by_distance[search_distance - 1][party][int(reference)]
            candidate: int | None = None
            best_payoff: float | None = None
            for value in ranked:
                offer_index = int(value)
                if offer_index in forbidden:
                    continue
                payoff = float(prepared.payoffs[offer_index, party])
                if candidate is None:
                    candidate = offer_index
                    best_payoff = payoff
                    continue
                if np.isclose(payoff, best_payoff):
                    candidate = min(candidate, offer_index)
                    continue
                # The neighborhood is already ordered by descending payoff.
                break
            if candidate is None:
                active[party] = False
                continue
            # Stable offer-index tie breaking keeps the ranked rule fully
            # reproducible while common random numbers govern all other
            # stochastic choices.
            register(party, candidate, scope)

        if prepared.consensus[candidate]:
            consensus_offers.add(int(candidate))
            if not agreement:
                agreement = True
                first_consensus_offer = int(candidate)
                first_consensus_step = len(history)
            if stop_rule == "first_consensus":
                termination = "agreement"

    if not termination:
        if agreement:
            termination = "settlement_offer_limit" if len(history) >= safety_limit else "settlement_exhausted"
        else:
            termination = "offer_limit" if len(history) >= safety_limit else "impasse"

    last_offer = history[-1] if history else None
    settlement_offer: int | None = None
    settlement_occurrence: int | None = None
    if agreement and consensus_offers:
        discovered = np.asarray(sorted(consensus_offers), dtype=np.int32)
        joint_payoffs = prepared.payoffs[discovered].sum(axis=1)
        best_joint = float(joint_payoffs.max())
        tied = discovered[np.isclose(joint_payoffs, best_joint)]
        settlement_offer = int(max(tied, key=lambda offer: last_occurrence[int(offer)]))
        settlement_occurrence = int(last_occurrence[settlement_offer])
        final_party_payoffs = prepared.payoffs[settlement_offer]
        mean_payoff = float(np.mean(final_party_payoffs))
    else:
        # Reservation payoff is the outside option on impasse.
        final_party_payoffs = np.asarray(prepared.scenario.reservations, dtype=float)
        mean_payoff = float(np.mean(final_party_payoffs))

    if agreement and first_consensus_offer is not None:
        first_party_payoffs = prepared.payoffs[first_consensus_offer]
        first_mean_payoff = float(np.mean(first_party_payoffs))
        first_joint_payoff = float(np.sum(first_party_payoffs))
        settlement_joint_payoff = float(np.sum(final_party_payoffs))
        settlement_gain = mean_payoff - first_mean_payoff
        post_consensus_offers = len(history) - int(first_consensus_step)
        first_pareto_efficient = int(
            prepared.pareto_efficient_consensus[int(first_consensus_offer)]
        )
        settlement_pareto_efficient = int(
            prepared.pareto_efficient_consensus[int(settlement_offer)]
        )
        best_joint = float(prepared.best_consensus_joint_payoff)
        if np.isfinite(best_joint) and best_joint > 1e-12:
            first_joint_ratio = first_joint_payoff / best_joint
            settlement_joint_ratio = settlement_joint_payoff / best_joint
        else:
            first_joint_ratio = 1.0
            settlement_joint_ratio = 1.0
    else:
        first_mean_payoff = np.nan
        first_joint_payoff = np.nan
        settlement_joint_payoff = float(np.sum(final_party_payoffs))
        settlement_gain = np.nan
        post_consensus_offers = 0
        first_pareto_efficient = np.nan
        settlement_pareto_efficient = np.nan
        first_joint_ratio = np.nan
        settlement_joint_ratio = np.nan

    return {
        "agreement": int(agreement),
        "agreement_step": int(first_consensus_step) if first_consensus_step is not None else np.nan,
        "first_consensus_step": int(first_consensus_step) if first_consensus_step is not None else np.nan,
        "offers_to_first_consensus": int(first_consensus_step) if first_consensus_step is not None else np.nan,
        "post_consensus_offers": int(post_consensus_offers),
        "offers": len(history),
        "termination": termination,
        "first_party": first_party,
        "first_consensus_offer": first_consensus_offer,
        "first_offer": history[0] if history else None,
        "first_offer_proposer": proposers[0] if proposers else None,
        "first_offer_scope": scopes[0] if scopes else None,
        "first_consensus_proposer": (
            proposers[int(first_consensus_step) - 1]
            if first_consensus_step is not None else None
        ),
        "first_consensus_scope": (
            scopes[int(first_consensus_step) - 1]
            if first_consensus_step is not None else None
        ),
        "final_offer": settlement_offer if agreement else last_offer,
        "settlement_offer": settlement_offer,
        "settlement_offer_proposer": (
            proposers[settlement_occurrence] if settlement_occurrence is not None else None
        ),
        "settlement_offer_scope": (
            scopes[settlement_occurrence] if settlement_occurrence is not None else None
        ),
        "last_offer": last_offer,
        "last_offer_proposer": proposers[-1] if proposers else None,
        "last_offer_scope": scopes[-1] if scopes else None,
        "mean_payoff": mean_payoff,
        "first_consensus_mean_payoff": first_mean_payoff,
        "first_consensus_joint_payoff": first_joint_payoff,
        "settlement_mean_payoff": mean_payoff,
        "settlement_joint_payoff": settlement_joint_payoff,
        "settlement_gain_mean_payoff": settlement_gain,
        "first_consensus_pareto_efficient": first_pareto_efficient,
        "settlement_pareto_efficient": settlement_pareto_efficient,
        "first_consensus_joint_payoff_ratio": first_joint_ratio,
        "settlement_joint_payoff_ratio": settlement_joint_ratio,
        "first_offer_rule": rule_name,
        "ambitious_top_k": ambitious_top_k,
        "reference_rule": reference_rule,
        "search_distance": search_distance,
        "local_search_rule": "proposer_ranked",
        "agreement_stopping_rule": stop_rule,
        "history": history,
        "proposers": proposers,
        "scopes": scopes,
    }


def run_streaming_experiment_summary(
    base_scenarios: Sequence[NegotiationScenario],
    *,
    group_sizes: Sequence[int],
    alphas: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    first_offer_rules: Sequence[str] = ("ambitious",),
    ambitious_top_ks: Sequence[int] = (3,),
    reference_rules: Sequence[int] = (1,),
    search_distances: Sequence[int] = (1,),
    agreement_stopping_rule: str = "first_consensus",
    runs_per_condition: int = 20,
    seed: int = 20260818,
    run_index_start: int = 0,
    deadlines: Sequence[int] = (5, 10, 15, 20, 30, 40, 60, 100),
    weak_acceptance: bool = True,
    progress: Callable[[int, int, str], None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run a memory-lean robustness grid and return condition summaries.

    Only one scenario × N landscape is prepared at a time.  Run histories are
    reduced immediately to agreement, duration, payoff, and deadline outcomes,
    which permits 100-scenario robustness grids without retaining hundreds of
    thousands of Python lists in memory.
    """
    condition_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    deadline_rows: list[dict[str, object]] = []
    total_cases = len(base_scenarios) * len(group_sizes)
    completed = 0

    for base_idx, base in enumerate(base_scenarios):
        for n_parties_value in group_sizes:
            n_parties = int(n_parties_value)
            scenario = base.subset_parties(n_parties)
            normalized_distances = tuple(int(x) for x in search_distances)
            if not normalized_distances:
                raise ValueError("search_distances cannot be empty.")
            prepared = prepare_scenario(
                scenario,
                max_search_distance=max(normalized_distances),
                weak_acceptance=bool(weak_acceptance),
            )
            metrics = scenario_metrics(prepared)
            metrics["base_scenario_id"] = base.scenario_id
            metric_rows.append(metrics)
            run_seeds = [
                int(seed + base_idx * 100_000 + n_parties * 1_000 + run_idx)
                for run_idx in range(int(run_index_start), int(run_index_start) + int(runs_per_condition))
            ]

            for first_offer_rule_value in first_offer_rules:
                for ambitious_top_k_value in ambitious_top_ks:
                    for reference_rule_value in reference_rules:
                        for search_distance_value in normalized_distances:
                            for alpha_value in alphas:
                                results = [
                                    simulate_once(
                                        prepared,
                                        alpha=float(alpha_value),
                                        seed=run_seed,
                                        first_offer_rule=str(first_offer_rule_value),
                                        ambitious_top_k=int(ambitious_top_k_value),
                                        reference_rule=int(reference_rule_value),
                                        search_distance=int(search_distance_value),
                                        agreement_stopping_rule=str(agreement_stopping_rule),
                                    )
                                    for run_seed in run_seeds
                                ]
                                agreements = np.asarray([r["agreement"] for r in results], dtype=float)
                                offers = np.asarray([r["offers"] for r in results], dtype=float)
                                offers_to_first = np.asarray([r["offers_to_first_consensus"] for r in results], dtype=float)
                                post_consensus_offers = np.asarray([r["post_consensus_offers"] for r in results], dtype=float)
                                payoffs = np.asarray([r["mean_payoff"] for r in results], dtype=float)
                                first_consensus_payoffs = np.asarray([r["first_consensus_mean_payoff"] for r in results], dtype=float)
                                settlement_gains = np.asarray([r["settlement_gain_mean_payoff"] for r in results], dtype=float)
                                first_pareto = np.asarray([r["first_consensus_pareto_efficient"] for r in results], dtype=float)
                                settlement_pareto = np.asarray([r["settlement_pareto_efficient"] for r in results], dtype=float)
                                first_joint_ratios = np.asarray([r["first_consensus_joint_payoff_ratio"] for r in results], dtype=float)
                                settlement_joint_ratios = np.asarray([r["settlement_joint_payoff_ratio"] for r in results], dtype=float)
                                agreement_steps = np.asarray([r["agreement_step"] for r in results], dtype=float)
                                normalized_fo = str(results[0]["first_offer_rule"]) if results else str(first_offer_rule_value)
                                row_keys = {
                                "base_scenario_id": base.scenario_id,
                                "scenario_id": scenario.scenario_id,
                                "N": n_parties,
                                "M": scenario.n_issues,
                                "alpha": float(alpha_value),
                                "first_offer_rule": normalized_fo,
                                "ambitious_top_k": int(ambitious_top_k_value),
                                "local_search_rule": "proposer_ranked",
                                "agreement_stopping_rule": str(results[0]["agreement_stopping_rule"]),
                                "reference_rule": int(reference_rule_value),
                                "search_distance": int(search_distance_value),
                                # Compatibility alias for the older Step 2/3 files.
                                "transition_rule": int(reference_rule_value),
                                **metrics,
                                }
                                agreed_mask = agreements.eq(1.0) if isinstance(agreements, pd.Series) else agreements == 1.0
                                condition_rows.append(
                                    {
                                        **row_keys,
                                        "agreement_rate": float(agreements.mean()),
                                        "mean_offers": float(offers.mean()),
                                        "mean_offers_if_agreement": float(offers[agreed_mask].mean()) if agreed_mask.any() else np.nan,
                                        "mean_offers_to_first_consensus": float(np.nanmean(offers_to_first)) if agreed_mask.any() else np.nan,
                                        "mean_post_consensus_offers_if_agreement": float(post_consensus_offers[agreed_mask].mean()) if agreed_mask.any() else np.nan,
                                        "expected_payoff": float(payoffs.mean()),
                                        "agreement_payoff": float(payoffs[agreed_mask].mean()) if agreed_mask.any() else np.nan,
                                        "first_consensus_payoff": float(np.nanmean(first_consensus_payoffs)) if agreed_mask.any() else np.nan,
                                        "payoff_gain_after_first_consensus": float(np.nanmean(settlement_gains)) if agreed_mask.any() else np.nan,
                                        "first_consensus_pareto_efficiency_rate": float(np.nanmean(first_pareto)) if agreed_mask.any() else np.nan,
                                        "settlement_pareto_efficiency_rate": float(np.nanmean(settlement_pareto)) if agreed_mask.any() else np.nan,
                                        "first_consensus_joint_payoff_ratio": float(np.nanmean(first_joint_ratios)) if agreed_mask.any() else np.nan,
                                        "settlement_joint_payoff_ratio": float(np.nanmean(settlement_joint_ratios)) if agreed_mask.any() else np.nan,
                                        "n_runs": int(runs_per_condition),
                                    }
                                )
                                for limit in deadlines:
                                    deadline_rows.append(
                                        {
                                            **row_keys,
                                            "offer_limit": int(limit),
                                            "agreement_rate": float(
                                                (np.isfinite(agreement_steps) & (agreement_steps <= int(limit))).mean()
                                            ),
                                            "n_runs": int(runs_per_condition),
                                        }
                                    )

            completed += 1
            if progress is not None:
                progress(completed, total_cases, scenario.scenario_id)

    return pd.DataFrame(condition_rows), pd.DataFrame(metric_rows), pd.DataFrame(deadline_rows)


def run_quick_experiment(
    base_scenarios: Sequence[NegotiationScenario],
    *,
    group_sizes: Sequence[int] = (2, 3, 4, 5, 6),
    alphas: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    runs_per_condition: int = 20,
    seed: int = 20260818,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run a paired 20-scenario design and return run- and scenario-level data."""
    cases = prepare_quick_experiment(base_scenarios, group_sizes=group_sizes)
    return run_prepared_experiment(
        cases,
        alphas=alphas,
        runs_per_condition=runs_per_condition,
        seed=seed,
    )


def prepare_quick_experiment(
    base_scenarios: Sequence[NegotiationScenario],
    *,
    group_sizes: Sequence[int] = (2, 3, 4, 5, 6),
) -> list[PreparedExperimentCase]:
    """Enumerate offers/neighbors and compute ruggedness once per structure."""
    cases: list[PreparedExperimentCase] = []
    for base in base_scenarios:
        for n_parties in group_sizes:
            scenario = base.subset_parties(int(n_parties))
            prepared = prepare_scenario(scenario)
            metrics = scenario_metrics(prepared)
            metrics["base_scenario_id"] = base.scenario_id
            cases.append(
                PreparedExperimentCase(
                    base_scenario_id=base.scenario_id,
                    prepared=prepared,
                    metrics=metrics,
                )
            )
    return cases


def run_prepared_experiment(
    cases: Sequence[PreparedExperimentCase],
    *,
    alphas: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    runs_per_condition: int = 20,
    seed: int = 20260818,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate already-prepared structures without repeating structural work."""
    run_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    base_order = {base_id: i for i, base_id in enumerate(dict.fromkeys(case.base_scenario_id for case in cases))}
    for case in cases:
        prepared = case.prepared
        scenario = prepared.scenario
        metrics = dict(case.metrics)
        metric_rows.append(metrics)
        base_idx = base_order[case.base_scenario_id]
        n_parties = scenario.n_parties
        # The same seed is used across alpha conditions for each run. This
        # creates a paired/common-random-number comparison where feasible.
        run_seeds = [int(seed + base_idx * 100_000 + n_parties * 1_000 + r) for r in range(runs_per_condition)]
        for alpha in alphas:
            for run_idx, run_seed in enumerate(run_seeds):
                result = simulate_once(prepared, alpha=float(alpha), seed=run_seed)
                run_rows.append(
                    {
                        "base_scenario_id": case.base_scenario_id,
                        "scenario_id": scenario.scenario_id,
                        "N": int(n_parties),
                        "M": scenario.n_issues,
                        "alpha": float(alpha),
                        "run": run_idx,
                        "seed": run_seed,
                        **metrics,
                        **result,
                    }
                )
    return pd.DataFrame(run_rows), pd.DataFrame(metric_rows)


def run_native_experiment(
    scenarios: Sequence[NegotiationScenario],
    *,
    alphas: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    runs_per_condition: int = 20,
    seed: int = 20260818,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run canonical/manual scenarios at each scenario's native party count."""
    run_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    for scenario_idx, scenario in enumerate(scenarios):
        prepared = prepare_scenario(scenario)
        metrics = scenario_metrics(prepared)
        metrics["base_scenario_id"] = scenario.scenario_id
        metric_rows.append(metrics)
        run_seeds = [int(seed + scenario_idx * 100_000 + r) for r in range(runs_per_condition)]
        for alpha in alphas:
            for run_idx, run_seed in enumerate(run_seeds):
                result = simulate_once(prepared, alpha=float(alpha), seed=run_seed)
                run_rows.append(
                    {
                        "base_scenario_id": scenario.scenario_id,
                        "scenario_id": scenario.scenario_id,
                        "N": scenario.n_parties,
                        "M": scenario.n_issues,
                        "alpha": float(alpha),
                        "run": run_idx,
                        "seed": run_seed,
                        **metrics,
                        **result,
                    }
                )
    return pd.DataFrame(run_rows), pd.DataFrame(metric_rows)


def summarize_experiment(
    runs: pd.DataFrame,
    *,
    deadlines: Sequence[int] = (5, 10, 15, 20, 30, 40, 60, 100),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create scenario-condition summaries and deadline agreement rates."""
    keys = [
        "base_scenario_id",
        "scenario_id",
        "N",
        "M",
        "alpha",
        "ruggedness",
        "ruggedness_possible_path",
        "zopa_count",
        "zopa_share",
    ]
    condition = (
        runs.groupby(keys, as_index=False)
        .agg(
            agreement_rate=("agreement", "mean"),
            mean_offers=("offers", "mean"),
            expected_payoff=("mean_payoff", "mean"),
            agreement_payoff=("mean_payoff", lambda s: float(s[runs.loc[s.index, "agreement"].eq(1)].mean()) if runs.loc[s.index, "agreement"].eq(1).any() else np.nan),
            n_runs=("agreement", "size"),
        )
    )

    deadline_rows: list[dict[str, object]] = []
    for key, block in runs.groupby(keys, sort=False):
        key_map = dict(zip(keys, key))
        steps = pd.to_numeric(block["agreement_step"], errors="coerce")
        for limit in deadlines:
            deadline_rows.append(
                {
                    **key_map,
                    "offer_limit": int(limit),
                    "agreement_rate": float(steps.le(limit).fillna(False).mean()),
                    "n_runs": len(block),
                }
            )
    return condition, pd.DataFrame(deadline_rows)


def fit_alpha_ruggedness_interaction(condition: pd.DataFrame, *, n_parties: int = 6) -> dict[str, float]:
    """Small-sample OLS diagnostic: AR ~ alpha + ruggedness + interaction."""
    d = condition.loc[condition["N"].eq(n_parties)].copy()
    r = pd.to_numeric(d["ruggedness"], errors="coerce").to_numpy(dtype=float)
    a = pd.to_numeric(d["alpha"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(d["agreement_rate"], errors="coerce").to_numpy(dtype=float)
    r_sd = float(np.std(r))
    rz = (r - float(np.mean(r))) / r_sd if r_sd > 0 else np.zeros_like(r)
    X = np.column_stack([np.ones(len(d)), a, rz, a * rz])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ beta
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {
        "intercept": float(beta[0]),
        "alpha": float(beta[1]),
        "ruggedness_z": float(beta[2]),
        "alpha_x_ruggedness_z": float(beta[3]),
        "r_squared": 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan,
        "n_condition_rows": int(len(d)),
    }


def analysis_tables(
    condition: pd.DataFrame,
    deadlines: pd.DataFrame,
) -> dict[str, pd.DataFrame | dict[str, float]]:
    """Build compact tables used by the notebook narrative and figures."""
    n6 = condition.loc[condition["N"].eq(6)].copy()
    scenario_rug = n6[["base_scenario_id", "ruggedness"]].drop_duplicates()
    median_rug = float(scenario_rug["ruggedness"].median())
    # Rank with deterministic tie breaking so both groups remain populated in
    # small validation runs or deliberately simple landscapes such as M=2.
    scenario_rug = scenario_rug.sort_values(["ruggedness", "base_scenario_id"]).reset_index(drop=True)
    split = int(math.ceil(len(scenario_rug) / 2)) if len(scenario_rug) else 0
    scenario_rug["ruggedness_group"] = np.where(
        np.arange(len(scenario_rug)) < split,
        "Lower ruggedness",
        "Higher ruggedness",
    )
    group_map = dict(
        zip(
            scenario_rug["base_scenario_id"],
            scenario_rug["ruggedness_group"],
        )
    )
    n6["ruggedness_group"] = n6["base_scenario_id"].map(group_map)
    alpha_by_ruggedness = (
        n6.groupby(["ruggedness_group", "alpha"], as_index=False)
        .agg(agreement_rate=("agreement_rate", "mean"), scenarios=("base_scenario_id", "nunique"))
    )

    extremes = n6.loc[n6["alpha"].isin([0.0, 1.0])]
    gap = (
        extremes.pivot_table(index=["base_scenario_id", "ruggedness"], columns="alpha", values="agreement_rate")
        .reset_index()
        .rename(columns={0.0: "alpha_0", 1.0: "alpha_1"})
    )
    gap["egocentric_minus_allocentric"] = gap["alpha_0"] - gap["alpha_1"]
    gap_corr = float(gap[["ruggedness", "egocentric_minus_allocentric"]].corr().iloc[0, 1])

    by_n = (
        condition.loc[condition["alpha"].isin([0.0, 1.0])]
        .groupby(["N", "alpha"], as_index=False)
        .agg(
            agreement_rate=("agreement_rate", "mean"),
            mean_offers=("mean_offers", "mean"),
            expected_payoff=("expected_payoff", "mean"),
            agreement_payoff=("agreement_payoff", "mean"),
            scenarios=("base_scenario_id", "nunique"),
        )
    )

    d6 = deadlines.loc[
        deadlines["N"].eq(6) & deadlines["alpha"].isin([0.0, 1.0])
    ].copy()
    d6["ruggedness_group"] = d6["base_scenario_id"].map(group_map)
    time_curves = (
        d6.groupby(["ruggedness_group", "alpha", "offer_limit"], as_index=False)
        .agg(agreement_rate=("agreement_rate", "mean"), scenarios=("base_scenario_id", "nunique"))
    )

    crossovers: list[dict[str, object]] = []
    for rug_group, block in time_curves.groupby("ruggedness_group"):
        wide = block.pivot(index="offer_limit", columns="alpha", values="agreement_rate").sort_index()
        eligible = wide.index[wide.get(0.0, pd.Series(index=wide.index, dtype=float)) >= wide.get(1.0, pd.Series(index=wide.index, dtype=float))]
        crossovers.append(
            {
                "ruggedness_group": rug_group,
                "first_tested_limit_ego_ge_allo": int(eligible.min()) if len(eligible) else np.nan,
            }
        )

    return {
        "alpha_by_ruggedness": alpha_by_ruggedness,
        "scenario_gap": gap,
        "group_size": by_n,
        "time_curves": time_curves,
        "crossovers": pd.DataFrame(crossovers),
        "interaction": fit_alpha_ruggedness_interaction(condition, n_parties=6),
        "gap_correlation": {"ruggedness_gap_correlation": gap_corr, "median_ruggedness": median_rug},
    }


def scenario_to_dict(scenario: NegotiationScenario) -> dict[str, object]:
    """JSON-safe representation for exact reproduction of generated inputs."""
    return {
        "scenario_id": scenario.scenario_id,
        "party_names": list(scenario.party_names),
        "issue_names": list(scenario.issue_names),
        "option_labels": [list(x) for x in scenario.option_labels],
        "issue_payoffs": [np.asarray(x).tolist() for x in scenario.issue_payoffs],
        "reservations": np.asarray(scenario.reservations).tolist(),
    }


def scenario_from_dict(record: dict[str, object]) -> NegotiationScenario:
    """Restore an exact scenario created by :func:`scenario_to_dict`."""
    return NegotiationScenario(
        scenario_id=str(record["scenario_id"]),
        party_names=tuple(str(x) for x in record["party_names"]),
        issue_names=tuple(str(x) for x in record["issue_names"]),
        option_labels=tuple(tuple(str(x) for x in labels) for labels in record["option_labels"]),
        issue_payoffs=tuple(np.asarray(values, dtype=float) for values in record["issue_payoffs"]),
        reservations=np.asarray(record["reservations"], dtype=float),
    )


def load_base_scenarios_json(path: str | Path) -> list[NegotiationScenario]:
    """Load the exact seeded scenario collection saved by this engine."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Scenario JSON must contain a list of scenario records.")
    return [scenario_from_dict(record) for record in records]


def save_base_scenarios_json(scenarios: Iterable[NegotiationScenario], path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps([scenario_to_dict(s) for s in scenarios], indent=2), encoding="utf-8")
    return path


def save_diagnostic_figure(
    tables: dict[str, pd.DataFrame | dict[str, float]],
    path: str | Path,
) -> Path:
    """Save a dependency-light four-panel PNG using Pillow.

    The notebook can be rerun in a minimal environment that lacks matplotlib.
    Users who prefer matplotlib can replace only this presentation function;
    no simulation or analysis logic depends on plotting.
    """
    from PIL import Image, ImageDraw, ImageFont

    path = Path(path)
    width, height = 1500, 1000
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        candidates = [
            Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=size)
        return ImageFont.load_default()

    f_title = font(28, True)
    f_panel = font(20, True)
    f_axis = font(16)
    f_tick = font(14)
    f_note = font(14)
    colors = {0.0: "#2166AC", 1.0: "#B2182B", "low": "#4C78A8", "high": "#E45756"}

    draw.text((55, 25), "Negotiation-as-search quick test: corrected alpha mechanism", fill="#222222", font=f_title)

    def line_panel(rect, title, xlabel, ylabel, series, x_domain=None, y_domain=(0.0, 1.0)):
        x0, y0, x1, y1 = rect
        left, top, right, bottom = x0 + 80, y0 + 55, x1 - 25, y1 - 65
        draw.text((x0 + 5, y0 + 5), title, fill="#222222", font=f_panel)
        draw.line((left, top, left, bottom), fill="#555555", width=2)
        draw.line((left, bottom, right, bottom), fill="#555555", width=2)
        all_x = [float(x) for item in series for x in item[1]]
        if x_domain is None:
            xmin, xmax = min(all_x), max(all_x)
        else:
            xmin, xmax = map(float, x_domain)
        ymin, ymax = map(float, y_domain)
        if xmax == xmin:
            xmax += 1.0
        if ymax == ymin:
            ymax += 1.0

        def px(x):
            return left + (float(x) - xmin) / (xmax - xmin) * (right - left)

        def py(y):
            return bottom - (float(y) - ymin) / (ymax - ymin) * (bottom - top)

        for frac in np.linspace(0, 1, 6):
            y = ymin + frac * (ymax - ymin)
            yy = py(y)
            draw.line((left, yy, right, yy), fill="#E8E8E8", width=1)
            draw.text((left - 52, yy - 8), f"{y:.1f}", fill="#555555", font=f_tick)

        unique_x = sorted(set(all_x))
        if len(unique_x) > 8:
            unique_x = unique_x[:: max(1, len(unique_x) // 7)]
            if unique_x[-1] != max(all_x):
                unique_x.append(max(all_x))
        for x in unique_x:
            xx = px(x)
            draw.line((xx, bottom, xx, bottom + 5), fill="#555555", width=1)
            label = f"{x:g}"
            draw.text((xx - 10, bottom + 9), label, fill="#555555", font=f_tick)

        legend_y = top + 8
        for label, xs, ys, color in series:
            points = [(px(x), py(y)) for x, y in zip(xs, ys)]
            if len(points) > 1:
                draw.line(points, fill=color, width=4, joint="curve")
            for xx, yy in points:
                draw.ellipse((xx - 5, yy - 5, xx + 5, yy + 5), fill=color, outline="white", width=1)
            draw.line((right - 145, legend_y + 7, right - 115, legend_y + 7), fill=color, width=4)
            draw.text((right - 108, legend_y - 2), str(label), fill="#333333", font=f_tick)
            legend_y += 23

        draw.text(((left + right) / 2 - 35, y1 - 35), xlabel, fill="#333333", font=f_axis)
        draw.text((x0 + 5, top - 25), ylabel, fill="#333333", font=f_axis)

    alpha_table = tables["alpha_by_ruggedness"]
    assert isinstance(alpha_table, pd.DataFrame)
    alpha_series = []
    for group, color in [("Lower ruggedness", colors["low"]), ("Higher ruggedness", colors["high"])]:
        block = alpha_table.loc[alpha_table["ruggedness_group"].eq(group)].sort_values("alpha")
        alpha_series.append((group.replace(" ruggedness", ""), block["alpha"], block["agreement_rate"], color))

    time_table = tables["time_curves"]
    assert isinstance(time_table, pd.DataFrame)
    time_series = []
    high_time = time_table.loc[time_table["ruggedness_group"].eq("Higher ruggedness")]
    for alpha in [0.0, 1.0]:
        block = high_time.loc[high_time["alpha"].eq(alpha)].sort_values("offer_limit")
        time_series.append((f"alpha={alpha:g}", block["offer_limit"], block["agreement_rate"], colors[alpha]))

    n_table = tables["group_size"]
    assert isinstance(n_table, pd.DataFrame)
    n_series = []
    for alpha in [0.0, 1.0]:
        block = n_table.loc[n_table["alpha"].eq(alpha)].sort_values("N")
        n_series.append((f"alpha={alpha:g}", block["N"], block["agreement_rate"], colors[alpha]))

    line_panel((45, 85, 745, 500), "A. Alpha by ruggedness (N=6)", "Alpha", "Agreement rate", alpha_series)
    line_panel((765, 85, 1465, 500), "B. Time boundary, higher ruggedness", "Offer limit", "Agreement rate", time_series)
    line_panel((45, 520, 745, 935), "C. Group size", "Negotiators (N)", "Agreement rate", n_series, x_domain=(2, 6))

    # Scatter panel: ruggedness versus alpha=0 minus alpha=1 agreement rate.
    gap = tables["scenario_gap"]
    assert isinstance(gap, pd.DataFrame)
    x0, y0, x1, y1 = 765, 520, 1465, 935
    left, top, right, bottom = x0 + 80, y0 + 55, x1 - 25, y1 - 65
    draw.text((x0 + 5, y0 + 5), "D. Ruggedness amplifies egocentric advantage", fill="#222222", font=f_panel)
    draw.line((left, top, left, bottom), fill="#555555", width=2)
    draw.line((left, bottom, right, bottom), fill="#555555", width=2)
    xs = gap["ruggedness"].to_numpy(dtype=float)
    ys = gap["egocentric_minus_allocentric"].to_numpy(dtype=float)
    xmin, xmax = 0.0, 1.0
    ymin, ymax = min(-0.05, float(ys.min()) - 0.05), max(0.75, float(ys.max()) + 0.05)

    def px(x): return left + (float(x) - xmin) / (xmax - xmin) * (right - left)
    def py(y): return bottom - (float(y) - ymin) / (ymax - ymin) * (bottom - top)

    for value in np.linspace(0, 1, 6):
        xx = px(value)
        draw.line((xx, bottom, xx, bottom + 5), fill="#555555", width=1)
        draw.text((xx - 12, bottom + 9), f"{value:.1f}", fill="#555555", font=f_tick)
    for value in np.linspace(0, 0.7, 5):
        yy = py(value)
        draw.line((left, yy, right, yy), fill="#E8E8E8", width=1)
        draw.text((left - 50, yy - 8), f"{value:.2f}", fill="#555555", font=f_tick)
    for x, y in zip(xs, ys):
        xx, yy = px(x), py(y)
        draw.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), fill="#6A51A3", outline="white", width=1)
    if len(xs) >= 2 and float(np.std(xs)) > 0:
        slope, intercept = np.polyfit(xs, ys, 1)
        line_x = np.asarray([xs.min(), xs.max()])
        line_y = intercept + slope * line_x
        draw.line([(px(x), py(y)) for x, y in zip(line_x, line_y)], fill="#222222", width=3)
    corr = tables["gap_correlation"]["ruggedness_gap_correlation"]  # type: ignore[index]
    draw.text((right - 130, top + 10), f"r = {corr:.2f}", fill="#333333", font=f_axis)
    draw.text(((left + right) / 2 - 45, y1 - 35), "Ruggedness", fill="#333333", font=f_axis)
    draw.text((x0 + 5, top - 25), "AR(alpha=0) - AR(alpha=1)", fill="#333333", font=f_axis)

    draw.text(
        (55, 966),
        "20 base scenarios; 20 runs per alpha x N condition; legacy Step 3 ruggedness shown.",
        fill="#555555",
        font=f_note,
    )
    image.save(path)
    return path


def save_payoff_figure(
    group_size_table: pd.DataFrame,
    path: str | Path,
) -> Path:
    """Plot expected versus agreement payoff at N=2 and N=6."""
    from PIL import Image, ImageDraw, ImageFont

    path = Path(path)
    image = Image.new("RGB", (1300, 600), "white")
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        candidates = [
            Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=size)
        return ImageFont.load_default()

    f_title = font(27, True)
    f_panel = font(20, True)
    f_axis = font(16)
    f_value = font(15, True)
    f_note = font(14)
    colors = {0.0: "#2166AC", 1.0: "#B2182B"}
    draw.text((45, 25), "Payoff risk-reward by group size", fill="#222222", font=f_title)

    def panel(rect, n_value: int):
        x0, y0, x1, y1 = rect
        block = group_size_table.loc[
            group_size_table["N"].eq(n_value) & group_size_table["alpha"].isin([0.0, 1.0])
        ].set_index("alpha")
        metrics = [("Expected payoff", "expected_payoff"), ("Agreement payoff", "agreement_payoff")]
        values = [float(block.loc[a, col]) for _, col in metrics for a in (0.0, 1.0)]
        ymax = max(values) * 1.20 if values else 1.0
        left, top, right, bottom = x0 + 85, y0 + 55, x1 - 30, y1 - 75
        draw.text((x0 + 5, y0 + 5), f"N = {n_value}", fill="#222222", font=f_panel)
        draw.line((left, top, left, bottom), fill="#555555", width=2)
        draw.line((left, bottom, right, bottom), fill="#555555", width=2)

        for frac in np.linspace(0, 1, 5):
            value = frac * ymax
            yy = bottom - frac * (bottom - top)
            draw.line((left, yy, right, yy), fill="#E8E8E8", width=1)
            draw.text((left - 63, yy - 8), f"{value:.2f}", fill="#555555", font=f_note)

        group_centers = [left + (right - left) * 0.30, left + (right - left) * 0.72]
        bar_width = 62
        for center, (label, col) in zip(group_centers, metrics):
            for offset, alpha in [(-bar_width, 0.0), (5, 1.0)]:
                value = float(block.loc[alpha, col])
                bar_left = center + offset
                bar_right = bar_left + bar_width - 6
                bar_top = bottom - value / ymax * (bottom - top)
                draw.rectangle((bar_left, bar_top, bar_right, bottom), fill=colors[alpha])
                draw.text((bar_left + 3, bar_top - 23), f"{value:.3f}", fill=colors[alpha], font=f_value)
            draw.text((center - 65, bottom + 16), label, fill="#333333", font=f_axis)

        legend_x = right - 155
        for i, alpha in enumerate([0.0, 1.0]):
            yy = top + i * 25
            draw.rectangle((legend_x, yy, legend_x + 18, yy + 14), fill=colors[alpha])
            draw.text((legend_x + 25, yy - 3), f"alpha={alpha:g}", fill="#333333", font=f_note)

    panel((40, 80, 640, 545), 2)
    panel((670, 80, 1270, 545), 6)
    draw.text(
        (45, 570),
        "Expected payoff includes impasses at the reservation value; agreement payoff conditions on agreement.",
        fill="#555555",
        font=f_note,
    )
    image.save(path)
    return path


def save_benchmark_comparison_figure(
    benchmark: pd.DataFrame,
    path: str | Path,
) -> Path:
    """Plot M-level timing and N=6 agreement comparisons."""
    from PIL import Image, ImageDraw, ImageFont

    path = Path(path)
    data = benchmark.sort_values("M").copy()
    image = Image.new("RGB", (1500, 700), "white")
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        candidates = [
            Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=size)
        return ImageFont.load_default()

    f_title = font(28, True)
    f_panel = font(20, True)
    f_axis = font(16)
    f_value = font(14, True)
    f_note = font(14)
    blue, red, gray = "#4C78A8", "#E45756", "#6B6B6B"
    draw.text((50, 25), "M benchmark: runtime and core agreement result", fill="#222222", font=f_title)

    def axes(rect, title, ymax, ylabel):
        x0, y0, x1, y1 = rect
        left, top, right, bottom = x0 + 85, y0 + 55, x1 - 25, y1 - 75
        draw.text((x0 + 5, y0 + 5), title, fill="#222222", font=f_panel)
        draw.line((left, top, left, bottom), fill="#555555", width=2)
        draw.line((left, bottom, right, bottom), fill="#555555", width=2)
        for frac in np.linspace(0, 1, 6):
            value = frac * ymax
            yy = bottom - frac * (bottom - top)
            draw.line((left, yy, right, yy), fill="#E8E8E8", width=1)
            draw.text((left - 58, yy - 8), f"{value:.1f}", fill="#555555", font=f_note)
        draw.text((x0 + 5, top - 25), ylabel, fill="#333333", font=f_axis)
        return left, top, right, bottom

    # Panel A: requested section timings plus end-to-end.
    rect = (40, 80, 745, 640)
    timing_max = float(data["end_to_end_seconds"].max()) * 1.18
    left, top, right, bottom = axes(rect, "A. Wall-clock time by section", timing_max, "Seconds")
    centers = np.linspace(left + 110, right - 110, len(data))
    bar_width = 42
    timing_specs = [
        ("Section 1", "section_1_total_seconds", blue, -67),
        ("Section 2", "section_2_total_seconds", red, -20),
        ("End-to-end", "end_to_end_seconds", gray, 27),
    ]
    for center, (_, row) in zip(centers, data.iterrows()):
        for label, col, color, offset in timing_specs:
            value = float(row[col])
            x_left = center + offset
            y_top = bottom - value / timing_max * (bottom - top)
            draw.rectangle((x_left, y_top, x_left + bar_width, bottom), fill=color)
            draw.text((x_left - 1, y_top - 20), f"{value:.2f}", fill=color, font=f_value)
        draw.text((center - 25, bottom + 18), f"M={int(row['M'])}", fill="#333333", font=f_axis)
    for i, (label, _, color, _) in enumerate(timing_specs):
        x = left + 12
        y = top + i * 25
        draw.rectangle((x, y, x + 18, y + 14), fill=color)
        draw.text((x + 25, y - 3), label, fill="#333333", font=f_note)

    # Panel B: N=6 alpha extremes.
    rect = (775, 80, 1470, 640)
    left, top, right, bottom = axes(rect, "B. N=6 agreement rate", 1.0, "Agreement rate")
    centers = np.linspace(left + 110, right - 110, len(data))
    result_specs = [
        ("alpha=0", "n6_alpha0_agreement", "#2166AC", -48),
        ("alpha=1", "n6_alpha1_agreement", "#B2182B", 8),
    ]
    for center, (_, row) in zip(centers, data.iterrows()):
        for label, col, color, offset in result_specs:
            value = float(row[col])
            x_left = center + offset
            y_top = bottom - value * (bottom - top)
            draw.rectangle((x_left, y_top, x_left + 48, bottom), fill=color)
            draw.text((x_left - 2, y_top - 22), f"{value:.3f}", fill=color, font=f_value)
        draw.text((center - 25, bottom + 18), f"M={int(row['M'])}", fill="#333333", font=f_axis)
    for i, (label, _, color, _) in enumerate(result_specs):
        x = right - 125
        y = top + i * 25
        draw.rectangle((x, y, x + 18, y + 14), fill=color)
        draw.text((x + 25, y - 3), label, fill="#333333", font=f_note)

    draw.text(
        (50, 665),
        "Each M: 20 base scenarios, N=2..6, five alpha values, 20 runs per condition (10,000 negotiations).",
        fill="#555555",
        font=f_note,
    )
    image.save(path)
    return path
