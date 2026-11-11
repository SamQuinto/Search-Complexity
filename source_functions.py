"""Replay five documented continuous or mixed negotiation calculations.

The numerical functions, grids and fixed Halton shifts follow the historical
source calculations. Search complexity uses every improving path through the
shared acceptance-grid calculation. Numerical payoffs and observed outcomes
are unchanged.
"""

import json
import math
from pathlib import Path

import numpy as np

from payoff_metrics import metrics_from_acceptance


SEED = 20260818


def first_primes(number):
    primes = []
    candidate = 2
    while len(primes) < number:
        if all(candidate % prime for prime in primes if prime * prime <= candidate):
            primes.append(candidate)
        candidate += 1
    return primes


def radical_inverse(index, base):
    value = 0.0
    factor = 1.0 / base
    while index:
        index, digit = divmod(index, base)
        value += digit * factor
        factor /= base
    return value


def halton(number, dimensions, seed=SEED):
    """Use the original un-scrambled sequence plus its fixed random shift."""
    bases = first_primes(dimensions)
    raw = np.asarray([[radical_inverse(index, base) for base in bases]
                      for index in range(1, number + 1)], dtype=float)
    shift = np.random.default_rng(seed).random(dimensions)
    return (raw + shift) % 1.0


def paired(first, second):
    return np.column_stack([np.asarray(first, dtype=float),
                            np.asarray(second, dtype=float)])


def payoff_grid(issues):
    """Preserve the source calculation's C-order issue addition."""
    shape = tuple(len(issue) for issue in issues)
    totals = np.zeros((int(np.prod(shape)), 2), dtype=float)
    for position, issue in enumerate(issues):
        inner = int(np.prod(shape[position + 1:]))
        outer = int(np.prod(shape[:position]))
        totals += np.tile(np.repeat(issue, inner, axis=0), (outer, 1))
    return totals, shape


def payment_profiles(periods=4, units=4):
    """Enumerate the original 25-percentage-point allocations across periods."""
    rows = []

    def allocate(remaining, slots, prefix):
        if slots == 1:
            rows.append(prefix + [remaining])
            return
        for value in range(remaining + 1):
            allocate(remaining - value, slots - 1, prefix + [value])

    allocate(units, periods, [])
    return np.asarray(rows, dtype=float) / units


def soccer_metrics(reservations):
    """Owner/player order, with the original separate volume and start samples."""
    volume_points = halton(16384, 3)
    owner = ((1 - volume_points[:, 0]) * 500000
             + (1 - volume_points[:, 1]) * 200000
             + (1 - volume_points[:, 2]) * 400000)
    player = (volume_points[:, 0] * 500000 + volume_points[:, 1] * 400000
              + volume_points[:, 2] * 200000)
    zone_share = ((owner >= reservations[0]) & (player >= reservations[1])).mean()
    salary = np.linspace(500000, 1000000, 501)
    signing = np.linspace(0, 200000, 201)
    goals = np.linspace(0, 20000, 21)
    issues = [paired(1000000 - salary, salary - 500000),
              paired(200000 - signing, 2 * signing),
              paired(20 * (20000 - goals), 10 * goals)]
    totals, shape = payoff_grid(issues)
    starting_points = halton(65536, 3)
    coordinates = np.minimum((starting_points * np.asarray(shape)).astype(int),
                             np.asarray(shape) - 1)
    starting_indices = np.ravel_multi_index(coordinates.T, shape)
    metrics = metrics_from_acceptance(totals >= np.asarray(reservations), shape, 2,
                                     starting_indices=starting_indices)
    metrics['bargaining_zone_share'] = float(zone_share)
    return metrics


def moms_grid(contingencies=None):
    """Return the historical grid in millions, net of the role alternatives.

    Buyer and seller alternative values are 3.0 and 2.5 million. Subtracting
    them in the functions makes zero the threshold for these net utilities.
    """
    prices = np.arange(35, 61, dtype=float)
    runs = np.asarray([4, 5, 6, 7, 8], dtype=float)
    profiles = payment_profiles()
    juniors = np.asarray([math.nan, 10, 12, 14, 16, 18, 20], dtype=float)
    shape = (len(prices), len(runs), len(profiles), len(juniors))
    if contingencies is not None:
        shape += (len(contingencies),)
    coordinates = np.indices(shape).reshape(len(shape), -1).T
    price = prices[coordinates[:, 0]]
    run = runs[coordinates[:, 1]]
    profile = profiles[coordinates[:, 2]]
    junior = juniors[coordinates[:, 3]]
    gross = price / 10.0
    buyer_discount = profile @ np.asarray([0.0, 0.10, 0.20, 0.30])
    seller_cost = profile @ np.asarray([0.0, 0.20, 0.35, 0.50])
    junior_buyer = np.where(np.isnan(junior), 0.0, (20.0 - junior) / 10.0)
    junior_seller = np.where(np.isnan(junior), 0.0, (junior - 10.0) / 10.0)
    buyer = 8.4 + 0.80 * (run - 6) - gross * (1.0 - buyer_discount) - 3.0 + junior_buyer
    seller = gross * (1.0 - seller_cost) - 0.25 * (run - 6) - 2.5 + junior_seller
    if contingencies is not None:
        contingency = contingencies[coordinates[:, 4]]
        buyer += contingency[:, 0]
        seller += contingency[:, 1]
    return np.column_stack([buyer, seller]), shape


def moms_standard_metrics():
    totals, shape = moms_grid()
    return metrics_from_acceptance(totals >= 0, shape, 2)


def moms_exp6_metrics():
    """Average the original four contingent-term strengths and sample settings."""
    observed = np.asarray([[0.0, 0.0], [-150000, 450000], [-1400000, 1400000],
                           [1890000, -690000], [50000, 1250000],
                           [600000, 600000], [450000, 1100000]], dtype=float) / 1000000
    points = halton(32768, 9, seed=SEED + 606)
    runs = np.asarray([4, 5, 6, 7, 8], dtype=float)
    rows = []
    for scale in [0.25, 0.50, 0.75, 1.00]:
        totals, shape = moms_grid(observed * scale)
        metrics = metrics_from_acceptance(totals >= 0, shape, 2)
        price = 35.0 + 25.0 * points[:, 0]
        run_indices = np.minimum((points[:, 1] * len(runs)).astype(int), len(runs) - 1)
        exponentials = -np.log(np.clip(points[:, 2:6], 1e-12, 1 - 1e-12))
        profiles = exponentials / exponentials.sum(axis=1, keepdims=True)
        junior_included = points[:, 6] >= 0.5
        junior = 10.0 + 10.0 * points[:, 7]
        contingency_indices = np.minimum((points[:, 8] * len(observed)).astype(int), len(observed) - 1)
        contingent = observed[contingency_indices] * scale
        gross = price / 10.0
        buyer = (8.4 + 0.80 * (runs[run_indices] - 6)
                 - gross * (1.0 - profiles @ np.asarray([0.0, 0.10, 0.20, 0.30]))
                 - 3.0 + np.where(junior_included, (20.0 - junior) / 10.0, 0.0)
                 + contingent[:, 0])
        seller = (gross * (1.0 - profiles @ np.asarray([0.0, 0.20, 0.35, 0.50]))
                  - 0.25 * (runs[run_indices] - 6) - 2.5
                  + np.where(junior_included, (junior - 10.0) / 10.0, 0.0)
                  + contingent[:, 1])
        metrics['bargaining_zone_share'] = float(((buyer >= 0) & (seller >= 0)).mean())
        rows.append(metrics)
    return {name: float(np.mean([row[name] for row in rows]))
            for name in ['bargaining_zone_share', 'search_complexity']}


def wolfe_metrics():
    """Recruiter/candidate order with four equally weighted reservation pairs."""
    discrete = [
        paired([0, 400, 800, 1200, 1600], [4000, 3000, 2000, 1000, 0]),
        paired([0, 1000, 2000, 3000, 4000], [1600, 1200, 800, 400, 0]),
        paired([0, 200, 400, 600, 800], [3200, 2400, 1600, 800, 0]),
        paired([0, 800, 1600, 2400, 3200], [800, 600, 400, 200, 0]),
    ]
    salary_points = np.linspace(0, 1, 101)
    totals, shape = payoff_grid([*discrete, paired(8000 * (1 - salary_points),
                                                8000 * salary_points)])
    points = halton(16384, 5, seed=SEED + 313)
    discrete_indices = np.minimum((points[:, :4] * 5).astype(int), 4)
    sampled = np.zeros((len(points), 2), dtype=float)
    for issue, table in enumerate(discrete):
        sampled += table[discrete_indices[:, issue]]
    sampled += np.column_stack([8000 * (1 - points[:, 4]), 8000 * points[:, 4]])
    rows = []
    for reservations in [(9500, 5000), (5000, 9500), (9500, 9500), (5000, 5000)]:
        metrics = metrics_from_acceptance(totals >= np.asarray(reservations), shape, 2)
        metrics['bargaining_zone_share'] = float((sampled >= np.asarray(reservations)).all(axis=1).mean())
        rows.append(metrics)
    return {name: float(np.mean([row[name] for row in rows]))
            for name in ['bargaining_zone_share', 'search_complexity']}


SOURCE_FUNCTION_SETTINGS = {
    'leonardelli_soccer_exp5_owner_high': {
        'reservation_values': [350000, 350000], 'role_order': ['owner', 'player'],
        'grid_shape': [501, 201, 21], 'bargaining_zone_draws': 16384,
        'starting_offer_draws': 65536, 'halton_shift_seed': SEED},
    'leonardelli_soccer_exp5_owner_low': {
        'reservation_values': [70000, 350000], 'role_order': ['owner', 'player'],
        'grid_shape': [501, 201, 21], 'bargaining_zone_draws': 16384,
        'starting_offer_draws': 65536, 'halton_shift_seed': SEED},
    'leonardelli_moms_exp6_reconstructed_contingency': {
        'grid_shape_per_scale': [26, 5, 35, 7, 7], 'contingency_scales': [0.25, 0.50, 0.75, 1.00],
        'bargaining_zone_draws_per_scale': 32768, 'halton_dimensions': 9,
        'halton_shift_seed': SEED + 606, 'scale_weights': [0.25, 0.25, 0.25, 0.25],
        'junior_inclusion_probability_in_volume_sample': 0.5},
    'moms_standard_four_issue_gunia_2013': {
        'grid_shape': [26, 5, 35, 7], 'possible_offers': 31850,
        'bargaining_zone_and_starting_offers': 'Full discrete grid'},
    'wolfe_mcginn_new_recruit_four_reservation_versions_pooled': {
        'reservation_pairs': [[9500, 5000], [5000, 9500], [9500, 9500], [5000, 5000]],
        'grid_shape': [5, 5, 5, 5, 101], 'bargaining_zone_draws_per_pair': 16384,
        'halton_shift_seed': SEED + 313, 'reservation_pair_weights': [0.25, 0.25, 0.25, 0.25]},
}


def calculate_formula_inputs(root):
    """Return the five source-function metrics with portable provenance."""
    catalogue_path = Path(root) / 'data' / 'raw_payoff_catalog.json'
    sources = {}
    if catalogue_path.is_file():
        sources = {entry['payoff_id']: entry['payoff_source']
                   for entry in json.loads(catalogue_path.read_text(encoding='utf-8'))}
    specifications = [
        ('leonardelli_soccer_exp5_owner_high', lambda: soccer_metrics((350000, 350000)),
         'Leonardelli et al. (2019), Experiment 5 supplement and scoring footnote'),
        ('leonardelli_soccer_exp5_owner_low', lambda: soccer_metrics((70000, 350000)),
         'Leonardelli et al. (2019), Experiment 5 supplement and scoring footnote'),
        ('leonardelli_moms_exp6_reconstructed_contingency', moms_exp6_metrics,
         'Leonardelli et al. (2019), Experiment 6 raw contingent terms and Moms.com role functions'),
        ('moms_standard_four_issue_gunia_2013', moms_standard_metrics,
         'Gunia et al. (2013), four-component Moms.com version and DRRC role functions'),
        ('wolfe_mcginn_new_recruit_four_reservation_versions_pooled', wolfe_metrics,
         'Wolfe and McGinn, printed five-issue schedule and four reservation conditions'),
    ]
    return [{'payoff_id': payoff_id, **calculation(),
             'input_type': 'Source payoff function with recorded grid and sampling',
             'source': sources.get(payoff_id, fallback)}
            for payoff_id, calculation, fallback in specifications]
