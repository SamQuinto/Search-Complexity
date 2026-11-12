"""Calculate structural measures for an additive discrete payoff schedule."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def metrics_from_acceptance(accepts, shape, required_approvals, mandatory_parties=(), starting_indices=None):
    """Trace every one-issue path that strictly increases the approval count."""
    accepts = np.asarray(accepts, dtype=bool)
    if accepts.ndim != 2 or len(accepts) != int(np.prod(shape)):
        raise ValueError('The acceptance rows do not match the offer grid')
    parties = accepts.shape[1]
    if not 1 <= required_approvals <= parties:
        raise ValueError('Invalid number of approvals required for agreement')
    votes = accepts.sum(axis=1).reshape(shape)
    acceptable = votes >= required_approvals
    if mandatory_parties:
        acceptable &= accepts[:, mandatory_parties].all(axis=1).reshape(shape)
    reachable = acceptable.copy()
    for level in range(parties - 1, -1, -1):
        targets = reachable & (votes > level)
        improving_neighbor = np.zeros(shape, dtype=bool)
        for issue in range(len(shape)):
            improving_neighbor |= targets.any(axis=issue, keepdims=True)
        reachable |= (votes == level) & improving_neighbor
    selected = reachable if starting_indices is None else reachable.ravel()[starting_indices]
    return {'bargaining_zone_share': float(acceptable.mean()),
            'search_complexity': float(1 - selected.mean()),
            'possible_offers': int(np.prod(shape))}


def replay_acceptance_inputs(source_dir):
    """Read the portable acceptance grids already coded from source materials."""
    source_dir = Path(source_dir)
    manifest = pd.read_csv(source_dir / 'metric_input_manifest.csv')
    records = []
    with np.load(source_dir / 'acceptance_inputs.npz', allow_pickle=False) as archive:
        for row in manifest.itertuples(index=False):
            shape = tuple(json.loads(row.grid_shape_json))
            bit_count = int(row.offer_count) * int(row.party_count)
            accepts = np.unpackbits(archive[row.archive_key], count=bit_count).reshape(
                int(row.offer_count), int(row.party_count))
            records.append({'payoff_id': row.payoff_id,
                            **metrics_from_acceptance(accepts, shape, int(row.required_acceptances)),
                            'input_type': 'Party-acceptance grid', 'source': row.source_locator})
    return records


def metrics_from_source_proof(proof):
    """Calculate from a supplied source proof, without needing a file path."""
    if proof['kind'] == 'all_payoffs_meet_reservations':
        lower = np.asarray(proof['lower_payoff_bounds'], dtype=float)
        reservations = np.asarray(proof['reservation_values'], dtype=float)
        if lower.shape != reservations.shape or not np.all(lower >= reservations):
            raise ValueError('The documented bounds do not prove acceptability for every party')
    elif proof['kind'] != 'all_complete_offers_allowed':
        raise ValueError('Unknown source-proof rule')
    return {'bargaining_zone_share': 1.0, 'search_complexity': 0.0}


def calculate_acceptability_proofs(path):
    """Use source inequalities or an explicit rule to establish acceptability."""
    return [{'payoff_id': proof['payoff_id'], **metrics_from_source_proof(proof),
             'input_type': 'Source-based acceptability proof', 'source': proof['source']}
            for proof in json.loads(Path(path).read_text(encoding='utf-8'))]


def metrics_from_programmed_rule(rule):
    """Calculate a supplied programmed rule without treating it as a seller RV."""
    shape = tuple(rule['shape'])
    choices = np.indices(shape).reshape(len(shape), -1)
    buyer = np.asarray(rule['buyer_score_coefficients']) @ choices
    accepts = np.column_stack([buyer >= rule['buyer_minimum'],
                               buyer <= rule['programmed_buyer_score_cap']])
    return metrics_from_acceptance(accepts, shape, 2)


def calculate_programmed_rules(path):
    """Calculate the documented main-sample reconstruction for a programmed rule."""
    records = []
    for rule in json.loads(Path(path).read_text(encoding='utf-8')):
        records.append({'payoff_id': rule['payoff_id'],
                        **metrics_from_programmed_rule(rule),
                        'input_type': 'Reconstructed programmed acceptance rule',
                        'source': rule['sources']})
    return records


def calculate_payoff_file(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    issues = [np.asarray(issue['payoffs'], dtype=float) for issue in record['issues']]
    shape = tuple(len(issue) for issue in issues)
    parties = len(record['reservation_values'])
    if any(issue.ndim != 2 or issue.shape[1] != parties for issue in issues):
        raise ValueError('An issue must supply a payoff for every party')
    choices = np.indices(shape).reshape(len(issues), -1)
    totals = sum(issue[choices[index]] for index, issue in enumerate(issues))
    accepts = totals >= np.asarray(record['reservation_values'])
    metrics = metrics_from_acceptance(accepts, shape, record['required_approvals'])
    compatible = sum(np.all(issue == issue.max(axis=0), axis=1).any() for issue in issues)
    return {'payoff_id': record['payoff_id'],
            **metrics,
            'number_of_issues': len(issues), 'number_of_parties': parties,
            'number_of_compatible_issues': int(compatible),
            'maximum_joint_payoff': float(totals.sum(axis=1).max()),
            'input_type': 'Option-level payoff schedule',
            'source': record['sources']['payoff_schedule']}


def calculate_catalog_inputs(catalog_path, structures, weights_path):
    """Replay additive tables with the documented reservation and approval rules.

    The catalogue also records entries whose complete calculation is unavailable.
    Those entries continue to use the recorded score and its source note.
    """
    catalogue = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    weight_table = pd.read_csv(weights_path)
    results, audit = [], []
    for entry in catalogue:
        payoff_id = entry['payoff_id']
        if not structures.payoff_id.eq(payoff_id).any():
            raise ValueError(f'The payoff catalogue names an unknown input: {payoff_id}')
        parts = entry.get('components', [])
        if not parts:
            continue
        calculated = []
        reason = ''
        for part in parts:
            schedule = part.get('schedule', {})
            if schedule.get('kind') != 'additive_discrete':
                reason = 'This entry needs its documented payoff-function calculation'
                break
            reservations = part.get('reservation_values')
            try:
                reservations = np.asarray([-np.inf if value == 'unbounded' else value
                                           for value in reservations], dtype=float)
            except (TypeError, ValueError):
                reason = 'A numerical reservation vector is not supplied for this component'
                break
            if reservations.ndim != 1 or not (np.isfinite(reservations) | np.isneginf(reservations)).all():
                reason = 'A numerical reservation vector is not supplied for this component'
                break
            issues = [np.asarray([option['payoffs'] for option in issue['options']], dtype=float)
                      for issue in schedule['issues']]
            if not issues or any(issue.ndim != 2 or issue.shape[1] != len(reservations) for issue in issues):
                raise ValueError(f'{payoff_id}: payoff columns do not match the reservation vector')
            approvals = part.get('required_approvals')
            if approvals is None:
                reason = 'The approval rule is not fully specified for this component'
                break
            shape = tuple(len(issue) for issue in issues)
            lower_bounds = sum(issue.min(axis=0) for issue in issues)
            if np.all(lower_bounds >= reservations):
                metrics = {'bargaining_zone_share': 1.0, 'search_complexity': 0.0,
                           'possible_offers': int(np.prod(shape))}
            else:
                if int(np.prod(shape)) > 2_000_000:
                    reason = 'This grid requires the compact acceptance input or another documented exact calculation'
                    break
                choices = np.indices(shape).reshape(len(issues), -1)
                totals = sum(issue[choices[index]] for index, issue in enumerate(issues))
                accepts = totals >= reservations
                metrics = metrics_from_acceptance(accepts, shape, int(approvals),
                                                  part.get('mandatory_parties', []))
            calculated.append(metrics)
            audit.append({'payoff_id': payoff_id, 'component': part.get('component', ''),
                          **metrics, 'reservation_values': json.dumps(reservations.tolist()),
                          'required_approvals': approvals,
                          'source': part.get('source_table_locator', entry['payoff_source'])})
        if reason or len(calculated) != len(parts):
            continue

        weights = [part.get('aggregation_weight') for part in parts]
        provided = all(weight is not None and np.isfinite(weight) for weight in weights)
        documented = weight_table.loc[weight_table.payoff_id.eq(payoff_id)]
        if not provided and len(documented) == len(parts) and set(documented.component) == {
                part.get('component', '') for part in parts}:
            values = documented.set_index('component').aggregation_weight
            weights = [values.loc[part['component']] for part in parts]
            provided = True
        same_metrics = all(np.ptp([value[name] for value in calculated]) <= 1e-12
                           for name in ['search_complexity', 'bargaining_zone_share'])
        if len(parts) == 1 or same_metrics:
            weights = np.ones(len(parts)) / len(parts)
        elif not provided:
            continue
        weights = np.asarray(weights, dtype=float)
        if not (weights >= 0).all() or not np.isclose(weights.sum(), 1, atol=1e-12, rtol=0):
            raise ValueError(f'{payoff_id}: the component weights do not sum to one')
        results.append({'payoff_id': payoff_id,
                        **{name: float(np.dot(weights, [value[name] for value in calculated]))
                           for name in ['search_complexity', 'bargaining_zone_share']},
                        'input_type': 'Option-level payoff catalogue',
                        'source': entry['payoff_source']})
    return results, pd.DataFrame(audit)
