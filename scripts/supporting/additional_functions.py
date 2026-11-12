"""Replay the Cartoon, bounded-reservation and scripted-acceptance measures."""

import json
from pathlib import Path

import numpy as np

from .payoff_metrics import metrics_from_acceptance
from .source_functions import first_primes, radical_inverse, payment_profiles, payoff_grid


def cartoon_metrics(record):
    model = record['payoff_function_input']
    variables, parameters = model['variables'], model['parameters']
    price_range = variables['price']
    prices = np.arange(price_range['minimum'], price_range['maximum'] + .1, price_range['grid_step'])
    runs = np.asarray(variables['runs'])
    periods = variables['payment_shares']['periods']
    profiles = payment_profiles(periods, 4)
    optional = np.asarray([np.nan, 10, 12, 14, 16, 18, 20])
    shape = (len(prices), len(runs), len(profiles), len(optional))
    coordinates = np.indices(shape).reshape(4, -1)

    def utilities(price, run_values, financing, side):
        gross = price / parameters['price_to_gross_divisor']
        buyer_discount = financing @ parameters['buyer_financing_rates']
        seller_cost = financing @ parameters['seller_financing_rates']
        side_buyer = np.where(np.isnan(side), 0, (20 - side) / 10)
        side_seller = np.where(np.isnan(side), 0, (side - 10) / 10)
        buyer = parameters['buyer_program_value'] + parameters['buyer_runs_step'] * (
            run_values - parameters['reference_runs']) - gross * (1 - buyer_discount) - parameters['buyer_reservation_value'] + side_buyer
        seller = gross * (1 - seller_cost) + parameters['seller_runs_step'] * (
            run_values - parameters['reference_runs']) - parameters['seller_reservation_value'] + side_seller
        return np.column_stack([buyer, seller])

    totals = utilities(prices[coordinates[0]], runs[coordinates[1]],
                       profiles[coordinates[2]], optional[coordinates[3]])
    metric = metrics_from_acceptance(totals >= 0, shape, 2)
    # The volume estimate uses the source's unshifted Halton points, with
    # continuous financing shares spread uniformly over their simplex.
    n = model['bargaining_zone_sampling']['sample_size']
    bases = first_primes(periods + 4)
    unit = np.asarray([[radical_inverse(index, base) for base in bases]
                       for index in range(1, n + 1)])
    sampled_prices = price_range['minimum'] + (price_range['maximum'] - price_range['minimum']) * unit[:, 0]
    sampled_runs = runs[np.minimum((unit[:, 1] * len(runs)).astype(int), len(runs) - 1)]
    exponentials = -np.log(np.clip(unit[:, 2:2 + periods], 1e-12, 1 - 1e-12))
    sampled_profiles = exponentials / exponentials.sum(axis=1, keepdims=True)
    side = np.where(unit[:, 2 + periods] >= .5, 10 + 10 * unit[:, 3 + periods], np.nan)
    sampled_totals = utilities(sampled_prices, sampled_runs, sampled_profiles, side)
    metric['bargaining_zone_share'] = float((sampled_totals >= 0).all(axis=1).mean())
    return metric


def kong_metrics(record):
    part = record['components'][0]
    issues = [np.asarray([option['payoffs'] for option in issue['options']], dtype=float)
              for issue in part['schedule']['issues']]
    totals, shape = payoff_grid(issues)
    results = []
    # Appendix 3 reports these two role-specific ranges. Their pairings are
    # unavailable, so the documented main-sample calculation averages all
    # 121 points in the fixed 11-by-11 range grid.
    for management in np.linspace(-15000, 23100, 11):
        for worker in np.linspace(-100000, 27000, 11):
            results.append(metrics_from_acceptance(totals >= [management, worker], shape, 2))
    return {name: float(np.mean([row[name] for row in results]))
            for name in ['bargaining_zone_share', 'search_complexity']}


def jaeger_metrics(record):
    model = record['payoff_function_input']
    management = np.asarray(model['management_item_values'])
    psychology = np.asarray(model['psychology_item_values'])
    shape = (2,) * len(management)
    packages = np.indices(shape).reshape(len(shape), -1).T
    first_total = packages @ management
    second_total = (1 - packages) @ psychology
    interest_advantage = packages @ (management - psychology)
    scripted_acceptance = (first_total > second_total) | (
        (first_total == second_total) & (interest_advantage > 0))
    accepts = np.column_stack([scripted_acceptance, np.ones(len(packages), dtype=bool)])
    return metrics_from_acceptance(accepts, shape, 2)


def calculate_additional_inputs(root):
    catalogue = {row['payoff_id']: row for row in json.loads(
        (Path(root) / 'data/raw_payoff_catalog.json').read_text(encoding='utf-8'))}
    specifications = [('cartoon_standard_us_us', cartoon_metrics),
                      ('kong_2011_disciplinary_bounded_rv_grid', kong_metrics),
                      ('jaeger_2017_resource_allocation_scripted_acceptance', jaeger_metrics)]
    return [{'payoff_id': payoff_id, **calculation(catalogue[payoff_id]),
             'input_type': 'Source payoff function with recorded grid and sampling',
             'source': catalogue[payoff_id]['payoff_source']}
            for payoff_id, calculation in specifications]
