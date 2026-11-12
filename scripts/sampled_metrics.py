"""Possible-path measures for a large additive two-party offer space.

Only the starting offers are sampled. The reachability check considers every
permitted alternative on each issue. With two parties, a strictly increasing
approval path has at most two changes: zero approvals, one, then two.
"""

import json
from pathlib import Path

import numpy as np
from .source_functions import halton as shifted_halton


def sampled_two_party_metrics(issues, reservations, n=65536, seed=20260827):
    issues = [np.asarray(issue, dtype=float) for issue in issues]
    reservations = np.asarray(reservations, dtype=float)
    if reservations.shape != (2,) or any(issue.shape[1] != 2 for issue in issues):
        raise ValueError('This calculation requires two-party additive payoffs')
    sizes = np.asarray([len(issue) for issue in issues])
    starts = np.minimum((shifted_halton(n, len(issues), seed) * sizes).astype(int), sizes - 1)
    current_values = [issue[starts[:, axis]] for axis, issue in enumerate(issues)]
    totals = sum(current_values)
    approvals = totals >= reservations
    agreement = approvals.all(axis=1)
    reachable = agreement.copy()

    # For each issue, sort Party A's values and retain the best Party B value
    # still available at or above each A threshold. A binary lookup then checks
    # all alternatives without constructing millions of neighboring packages.
    frontiers = []
    for issue in issues:
        order = np.argsort(issue[:, 0])
        a = issue[order, 0]
        best_b = np.r_[np.maximum.accumulate(issue[order, 1][::-1])[::-1], -np.inf]
        frontiers.append((a, best_b))

    def one_change_reaches(indices, payoffs, omit_issue=None):
        result = np.zeros(len(indices), dtype=bool)
        for axis, (a, best_b) in enumerate(frontiers):
            if axis == omit_issue:
                continue
            needed = reservations - payoffs + current_values[axis][indices]
            alternatives = np.searchsorted(a, needed[:, 0], side='left')
            result |= best_b[alternatives] >= needed[:, 1]
        return result

    remaining = np.flatnonzero(~agreement)
    reachable[remaining] = one_change_reaches(remaining, totals[remaining])
    zero_approvals = ~approvals.any(axis=1)
    for first_issue, options in enumerate(issues):
        for option in options:
            remaining = np.flatnonzero(zero_approvals & ~reachable)
            if not len(remaining):
                break
            revised = totals[remaining] + option - current_values[first_issue][remaining]
            improved = (revised >= reservations).any(axis=1)
            selected = remaining[improved]
            if len(selected):
                second_change = one_change_reaches(selected, revised[improved], omit_issue=first_issue)
                reachable[selected[second_change]] = True
    return {'bargaining_zone_share': float(agreement.mean()),
            'search_complexity': float(1 - reachable.mean()),
            'possible_offers': int(np.prod(sizes)), 'sampled_starting_offers': n, 'seed': seed}


def calculate_player_input(catalogue_path):
    records = json.loads(Path(catalogue_path).read_text(encoding='utf-8'))
    entry = next(row for row in records if row['payoff_id'] == 'kray2004_player_two_power_orders_pooled')
    components = []
    for part in entry['components']:
        issues = [np.asarray([option['payoffs'] for option in issue['options']], dtype=float)
                  for issue in part['schedule']['issues']]
        components.append(sampled_two_party_metrics(issues, part['reservation_values']))
    weights = np.asarray([part['aggregation_weight'] for part in entry['components']])
    if not np.isclose(weights.sum(), 1, atol=1e-12, rtol=0):
        raise ValueError('Player reservation-order weights do not sum to one')
    combined = {'payoff_id': entry['payoff_id'],
                **{name: float(np.dot(weights, [row[name] for row in components]))
                   for name in ['bargaining_zone_share', 'search_complexity']},
                'input_type': 'Sampled starts with complete two-party path checks',
                'source': entry['payoff_source']}
    return combined, components
