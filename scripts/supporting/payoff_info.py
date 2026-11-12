"""Read the self-contained payoff_json cells and replay the released measures.

Run: python scripts/supporting/payoff_info.py --observation SRU0286
     python scripts/supporting/payoff_info.py --check

No formula text is executed. Named, versioned source-function calculators are
reused; unsupported edits to their model specifications are rejected.
"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import argparse
import csv
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.supporting.payoff_metrics import (metrics_from_acceptance,
                                              metrics_from_programmed_rule,
                                              metrics_from_source_proof)

COLUMN = 'payoff_json'
MEASURES = ['search_complexity', 'bargaining_zone_share', 'number_of_issues',
            'number_of_parties', 'number_of_compatible_issues']
# The fixed historical function implementations accept these released model
# specifications. A changed formula must acquire an implementation, rather
# than silently reusing hard-coded coefficients from a different model.
FUNCTION_CONTRACTS = {
    'sale_cafe_buyer_cap_1550': '5a4b2cfc44b09a044fd4581ae26bb2eedfb8084ff49e24aa2a2cb8d7966ddcf8',
    'sale_cafe_buyer_cap_3500': '704229f4c7f200508c7ff5a35fb808de57fd528af60aeaeef77cc87eb4337e5b',
    'sale_cafe_buyer_cap_5450': '720d28616225a008a0800f5325c299a1dfb37954304119aee4b436a3967b12cb',
    'sale_cafe_buyer_cap_7400': '8c7210d93c9db32d16a740f664ba27a41562d8ba8551416ec1fca924619fe6bb',
    'wolfe_mcginn_new_recruit_four_reservation_versions_pooled': 'b59f71105752e78e3a6e67a851ba79793e3baf940d4a960fb1b75de152cadb20',
    'leonardelli_soccer_exp5_owner_high': '4b64e8c82a5eafd097e082e2c67cb8895c77ab90aa3e7b91d6a4241b16fbc4f7',
    'cartoon_standard_us_us': 'ebe14a222aeed90abfb6ba65852babb7e7c96f6fc4215a3b8b3ed3ef5a8f5b4b',
    'leonardelli_moms_exp6_reconstructed_contingency': 'aadf38711200dfb88f5740202a24b13dc4ed5b8a3061c2b5b3b37df52105cfa6',
    'leonardelli_soccer_exp5_owner_low': '1a97978afdb64f6b18cb778445afe2e360d38f47f74055a61e0d1bedca8b5ca9',
    'moms_standard_four_issue_gunia_2013': '4584b88a83b9ed03f4fae36705182b250eca182ad487b37d479e9e365f3cf79f',
    'jaeger_2017_resource_allocation_scripted_acceptance': '55806cdb00c5f520789a82c27c285e29ed5ecd4ec77ad4199d436358faa7211a',
}


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return sha256(encoded.encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pack_catalog(entry):
    """Use nested payoff arrays and store repeated pooled schedules once."""
    entry = json.loads(dumps(entry))
    schedules = {}
    for part in entry.get('components', []):
        schedule = part.pop('schedule')
        key = 't' + fingerprint(schedule)[:16]
        if key not in schedules:
            schedules[key] = {**schedule, 'issues': [
                {'name': issue['name'], 'options': [o['option'] for o in issue['options']],
                 'payoffs': [o['payoffs'] for o in issue['options']]}
                for issue in schedule['issues']]}
        part['schedule_ref'] = key
    if schedules:
        entry['schedules'] = schedules
    return entry


def unpack_catalog(entry):
    """Restore the existing calculator's table structure, without file reads."""
    entry = json.loads(dumps(entry))
    schedules = entry.pop('schedules', {})
    for part in entry.get('components', []):
        if 'schedule_ref' not in part:
            continue
        schedule = schedules[part.pop('schedule_ref')]
        issues = []
        for issue in schedule['issues']:
            if len(issue['options']) != len(issue['payoffs']):
                raise ValueError('Each option label needs one payoff row.')
            issues.append({'name': issue['name'], 'options': [
                {'option': label, 'payoffs': row} for label, row in
                zip(issue['options'], issue['payoffs'])]})
        part['schedule'] = {**schedule, 'issues': issues}
    return entry


def input_records(root):
    """Join raw inputs and explicit coding evidence, never structural_scores."""
    root = Path(root)
    catalog = read_json(root / 'data/raw_payoff_catalog.json')
    proofs = {r['payoff_id']: r for r in read_json(root / 'data/acceptability_proofs.json')}
    programmed = {r['payoff_id']: r for r in read_json(root / 'data/programmed_acceptance_rules.json')}
    schedules = {r['payoff_id']: r for r in
                 [read_json(path) for path in sorted((root / 'data/payoff_schedules').glob('*.json'))]}
    structures = pd.read_csv(root / 'data/sources/structure_inputs.csv').set_index('payoff_id')
    active_ids = {entry['payoff_id'] for entry in catalog}
    if len(active_ids) != len(catalog) or active_ids != set(structures.index[structures.main_eligible.eq(True)]):
        raise ValueError('The active payoff catalogue must match the eligible structures; excluded source records stay in the inventory.')
    approval = pd.read_csv(root / 'data/approval_rules.csv').fillna('').set_index('payoff_id')
    allocation = pd.read_csv(root / 'data/within_payoff_weights.csv').astype(object)
    allocation = allocation.where(allocation.notna(), None)
    from scripts.supporting.source_functions import SOURCE_FUNCTION_SETTINGS
    records = {}
    for entry in catalog:
        payoff_id = entry['payoff_id']
        coded = structures.loc[payoff_id]
        value = {'catalog': entry,
                 'coverage': 'numerical' if entry.get('components') or entry.get('payoff_function_input') else 'proof_only',
                 'source_coding': {name: float(coded[name]) for name in MEASURES[2:]},
                 'coding_source': entry['payoff_source'],
                 'approval': approval.loc[payoff_id].to_dict()}
        if payoff_id in proofs:
            value['proof'] = proofs[payoff_id]
        if payoff_id in programmed:
            value['programmed_rule'] = programmed[payoff_id]
        if payoff_id in schedules:
            value['option_value_schedule'] = schedules[payoff_id]
        if payoff_id in SOURCE_FUNCTION_SETTINGS:
            value['calculation_settings'] = SOURCE_FUNCTION_SETTINGS[payoff_id]
        documented_weights = allocation.loc[allocation.payoff_id.eq(payoff_id)]
        if len(documented_weights):
            value['within_payoff_allocation'] = documented_weights.drop(columns='payoff_id').to_dict('records')
        if entry.get('payoff_function_input') or not entry.get('components'):
            # Function and proof records use the documented two-party unanimity
            # convention. This is an approval rule, not an invented payoff/RV.
            if coded['number_of_parties'] != 2 or approval.loc[payoff_id, 'non_unanimous_share'] != 0:
                raise ValueError(f'{payoff_id}: encode its approval rule explicitly.')
            value['required_approvals'] = 2
        if value['coverage'] == 'proof_only':
            value['input_issues'] = ['complete_numerical_schedule_missing']
        if payoff_id == 'kray2004_player_two_power_orders_pooled':
            value['calculation_settings'] = {'starting_offer_draws': 65536, 'seed': 20260827,
                                             'method': 'Sampled starts; all permitted two-party path changes'}
        value['catalog'] = pack_catalog(entry)
        validate_controls(record_controls(value), value['source_coding'], payoff_id)
        records[payoff_id] = value
    return records


def attach_payoff_info(frame, root, components):
    """Add the JSON column directly after the ID, retaining all numeric values."""
    frame = frame.copy()
    records = input_records(root)
    values = {}
    for study_id, rows in components.groupby('study_id', sort=False):
        complete = rows.negotiations.notna().all() and rows.negotiations.gt(0).all()
        counts = rows.negotiations.to_numpy(float) if complete else np.ones(len(rows))
        weights = counts / counts.sum()
        ids = list(dict.fromkeys(rows.payoff_id))
        for name in MEASURES[2:]:
            expected = float(np.dot(weights, [records[i]['source_coding'][name] for i in rows.payoff_id]))
            for observation in frame.loc[frame.observation_id.eq(study_id)].itertuples(index=False):
                actual = float(getattr(observation, name))
                if not np.isclose(actual, expected, atol=1e-12, rtol=0):
                    raise ValueError(f'{study_id}: {name} differs from verified payoff/source controls; rebuild the coded data.')
        payload = {'schema_version': 1,
                   'coverage': 'numerical' if all(records[i]['coverage'] == 'numerical' for i in ids) else 'includes_proof_only',
                   'weighting': 'negotiation_counts' if complete else 'equal_documented_components',
                   'components': [{'component_id': str(row.component_id), 'payoff_id': str(row.payoff_id),
                                   'negotiations': None if pd.isna(row.negotiations) else float(row.negotiations),
                                   'weight': float(weight)} for row, weight in zip(rows.itertuples(index=False), weights)],
                   'payoffs': {i: records[i] for i in ids}}
        values[study_id] = dumps(payload)
    if not set(frame.observation_id).issubset(values):
        raise ValueError('An observation has no component-level payoff inputs.')
    if COLUMN in frame:
        frame = frame.drop(columns=COLUMN)
    frame.insert(1, COLUMN, frame.observation_id.map(values))
    return frame


def table_controls(issues, parties):
    compatible = sum(np.all(issue == issue.max(axis=0), axis=1).any() for issue in issues)
    return {'number_of_issues': len(issues), 'number_of_parties': parties,
            'number_of_compatible_issues': int(compatible)}


def validate_controls(actual, coded, payoff_id):
    for name in MEASURES[2:]:
        if actual.get(name) is None or not np.isclose(actual[name], coded[name], atol=1e-12, rtol=0):
            raise ValueError(f'{payoff_id}: {name} from payoff/source evidence ({actual.get(name)}) '
                             f'disagrees with source coding ({coded[name]}). Check physical option alignment and source evidence.')


def reported_controls(proof):
    counts = proof.get('source_verified_controls', {})
    keys = ['issues', 'parties', 'compatible']
    if set(counts) != set(keys) or not proof.get('controls_source'):
        raise ValueError('A proof-only input needs directly reported controls and exact source pages.')
    if any(type(counts[k]) is not int or counts[k] < 0 for k in keys):
        raise ValueError('Reported control counts must be nonnegative integers.')
    if counts['issues'] < 2 or counts['parties'] < 2 or counts['compatible'] > counts['issues']:
        raise ValueError('Invalid directly reported control counts.')
    return dict(zip(MEASURES[2:], [counts[k] for k in keys]))


def record_controls(record):
    """Validate tables/formulas or directly reported proof controls cheaply."""
    entry = unpack_catalog(record['catalog'])
    if record['coverage'] == 'proof_only':
        return reported_controls(record['proof'])
    model = entry.get('payoff_function_input')
    if model is not None:
        if fingerprint(model) != FUNCTION_CONTRACTS.get(entry['payoff_id']):
            raise ValueError(f"{entry['payoff_id']}: changed/unsupported source function.")
        return function_controls(model, record)
    rows = [table_controls([np.asarray([o['payoffs'] for o in issue['options']])
                            for issue in part['schedule']['issues']], len(part['schedule']['parties']))
            for part in entry['components']]
    weights = [part.get('aggregation_weight') for part in entry['components']]
    if any(w is None for w in weights):
        if not all(np.ptp([row[name] for row in rows]) <= 1e-12 for name in MEASURES[2:]):
            raise ValueError('Unknown allocation changes a requested control.')
        weights = np.ones(len(rows)) / len(rows)
    if not np.isclose(sum(weights), 1, atol=1e-12, rtol=0) or any(w < 0 for w in weights):
        raise ValueError('Within-payoff weights must sum to one.')
    return {name: float(np.dot(weights, [r[name] for r in rows])) for name in MEASURES[2:]}


def table_parts(entry, settings=None):
    """Calculate tables without reading a saved acceptance grid or score."""
    results = []
    for part in entry['components']:
        if part['schedule']['kind'] != 'additive_discrete':
            raise ValueError('Unsupported table kind.')
        reservations = part['reservation_values']
        if reservations is None:
            raise ValueError('This component needs its formula or reservation-grid calculator.')
        reservations = np.asarray([-np.inf if v == 'unbounded' else v for v in reservations], dtype=float)
        issues = [np.asarray([o['payoffs'] for o in issue['options']], dtype=float)
                  for issue in part['schedule']['issues']]
        if any(x.ndim != 2 or x.shape[1] != len(reservations) for x in issues):
            raise ValueError('An issue does not contain one payoff per party.')
        shape = tuple(len(issue) for issue in issues)
        if settings and settings.get('method', '').startswith('Sampled starts'):
            from scripts.supporting.sampled_metrics import sampled_two_party_metrics
            metric = sampled_two_party_metrics(issues, reservations, settings['starting_offer_draws'], settings['seed'])
        elif np.all(sum(issue.min(axis=0) for issue in issues) >= reservations):
            metric = {'search_complexity': 0., 'bargaining_zone_share': 1.}
        else:
            if int(np.prod(shape)) > 2_000_000:
                raise ValueError('Large offer space has no declared sampling calculator.')
            choices = np.indices(shape).reshape(len(shape), -1)
            totals = sum(issue[choices[i]] for i, issue in enumerate(issues))
            metric = metrics_from_acceptance(totals >= reservations, shape, part['required_approvals'],
                                             part.get('mandatory_parties', []))
        results.append({**metric, **table_controls(issues, len(reservations))})
    weights = [part.get('aggregation_weight') for part in entry['components']]
    if any(weight is None for weight in weights):
        if not all(np.ptp([row[name] for row in results]) <= 1e-12 for name in MEASURES):
            raise ValueError('Unknown within-payoff allocation changes a requested measure.')
        weights = np.ones(len(results)) / len(results)
    weights = np.asarray(weights, dtype=float)
    if not np.isclose(weights.sum(), 1, atol=1e-12, rtol=0) or (weights < 0).any():
        raise ValueError('Within-payoff component weights do not sum to one.')
    return {name: float(np.dot(weights, [r[name] for r in results])) for name in MEASURES}


def function_metrics(entry, record):
    """Use the released named implementations, with a model-contract check."""
    from scripts.supporting import source_functions as source
    from scripts.supporting import additional_functions as additional
    payoff_id = entry['payoff_id']
    model = entry.get('payoff_function_input')
    if model is not None and record.get('required_approvals') != 2:
        raise ValueError('The registered function requires the documented two-party approval rule.')
    if model is not None and fingerprint(model) != FUNCTION_CONTRACTS.get(payoff_id):
        raise ValueError(f'{payoff_id}: changed/unsupported source function; extend its calculator explicitly.')
    if payoff_id in source.SOURCE_FUNCTION_SETTINGS and record.get('calculation_settings') != source.SOURCE_FUNCTION_SETTINGS[payoff_id]:
        raise ValueError('The registered function requires its declared released numerical procedure.')
    if payoff_id.startswith('sale_cafe_buyer_cap_'):
        metric = metrics_from_programmed_rule(record['programmed_rule'])
    elif payoff_id.startswith('leonardelli_soccer_exp5_owner_'):
        metric = source.soccer_metrics(model['reservation_values'])
    elif payoff_id == 'cartoon_standard_us_us':
        metric = additional.cartoon_metrics(entry)
    elif payoff_id == 'moms_standard_four_issue_gunia_2013':
        metric = source.moms_standard_metrics()
    elif payoff_id == 'leonardelli_moms_exp6_reconstructed_contingency':
        metric = source.moms_exp6_metrics()
    elif payoff_id == 'wolfe_mcginn_new_recruit_four_reservation_versions_pooled':
        metric = source.wolfe_metrics()
    elif payoff_id == 'jaeger_2017_resource_allocation_scripted_acceptance':
        metric = additional.jaeger_metrics(entry)
    elif payoff_id == 'kong_2011_disciplinary_bounded_rv_grid':
        grid = entry['reservation_value_grid']
        if not (np.allclose(grid['management_values'], np.linspace(-15000, 23100, 11), atol=0, rtol=0)
                and np.allclose(grid['worker_values'], np.linspace(-100000, 27000, 11), atol=0, rtol=0)):
            raise ValueError('The recorded Kong grid changed; extend its named calculator explicitly.')
        metric = additional.kong_metrics(entry)
        part = entry['components'][0]
        issues = [np.asarray([o['payoffs'] for o in i['options']]) for i in part['schedule']['issues']]
        return {**metric, **table_controls(issues, len(part['schedule']['parties']))}
    else:
        raise ValueError(f'No released function calculator for {payoff_id}.')
    return {**metric, **function_controls(model, record)}


def function_controls(model, record):
    """Read logical issue counts and preferences from the registered model.

    Optional Juniors is one logical issue with a common-benefit inclusion
    direction and an opposed price within that choice. Financing shares are
    one simplex-valued issue, rather than one issue per payment period.
    """
    payoff_id = record['catalog']['payoff_id']
    parties = len(model['parties'])
    if payoff_id.startswith('sale_cafe_'):
        rule = record['programmed_rule']
        slopes = zip(rule['buyer_score_coefficients'], rule['seller_total_function']['coefficients'])
        issues = [np.array([[0, 0], [a, b]]) for a, b in slopes]
    elif payoff_id.startswith('leonardelli_soccer_'):
        v = model['variables']
        salary = v['salary']['maximum'] - v['salary']['minimum']
        signing = v['signing_bonus']['maximum'] - v['signing_bonus']['minimum']
        goals = v['goal_bonus']['maximum'] - v['goal_bonus']['minimum']
        issues = [np.array([[0, 0], [-salary, salary]]),
                  np.array([[0, 0], [-signing, 2 * signing]]),
                  np.array([[0, 0], [-20 * goals, 10 * goals]])]
    elif 'management_item_values' in model:
        issues = [np.array([[0, p], [m, 0]]) for m, p in
                  zip(model['management_item_values'], model['psychology_item_values'])]
    elif 'discrete_issue_tables' in model:
        issues = [np.asarray([o['payoffs'] for o in i['options']])
                  for i in model['discrete_issue_tables']['issues']]
        # The registered salary formulas are 8000*(1-q) and 8000*q.
        issues.append(np.array([[8000, 0], [0, 8000]]))
    else:
        p, v = model['parameters'], model['variables']
        issues = [np.array([[0, 0], [-1, 1]]) / p['price_to_gross_divisor'],
                  np.array([[0, 0], [p['buyer_runs_step'], p['seller_runs_step']]]),
                  np.column_stack([p['buyer_financing_rates'], -np.asarray(p['seller_financing_rates'])])]
        if 'contingency_pairs_millions' in model:
            issues.append(np.asarray(model['contingency_pairs_millions']))
        side = v['optional_juniors_price']
        side_prices = np.asarray([x for x in side['grid_options'] if isinstance(x, (int, float))])
        benefits = np.column_stack([(side['maximum'] - side_prices) / 10,
                                    (side_prices - side['minimum']) / 10])
        common_inclusion_direction = bool((benefits >= 0).all() and (benefits > 0).all(axis=1).any())
        counts = table_controls(issues, parties)
        counts['number_of_issues'] += 1
        counts['number_of_compatible_issues'] += int(common_inclusion_direction)
        return counts
    return table_controls(issues, parties)


@lru_cache(maxsize=256)
def calculate_record(serialized):
    record = json.loads(serialized)
    entry = unpack_catalog(record['catalog'])
    payoff_id = entry['payoff_id']
    warnings = [entry['needed_piece']] if entry.get('needed_piece') else []
    if record['coverage'] == 'proof_only':
        values = metrics_from_source_proof(record['proof'])
        values.update(reported_controls(record['proof']))
        basis = 'Directly reported source controls; complete numerical schedules unavailable. ' + record['proof']['controls_source']
    elif entry.get('payoff_function_input') or payoff_id == 'kong_2011_disciplinary_bounded_rv_grid':
        values = function_metrics(entry, record)
        basis = 'Logical issues in the documented formula; optional Juniors inclusion is the common-benefit direction in Cartoon/Moms.com.'
        note = entry.get('payoff_function_input', {}).get('reconstruction_note')
        if note:
            warnings.append(note)
    else:
        values = table_parts(entry, record.get('calculation_settings'))
        basis = 'Shared best choice in the supplied additive-utility table; all parties maximize the encoded payoff.'
    coded = record['source_coding']['number_of_compatible_issues']
    validate_controls(values, record['source_coding'], payoff_id)
    return {**{name: values[name] for name in MEASURES},
            'coded_number_of_compatible_issues': coded,
            'control_basis': basis, 'warnings': warnings}


def calculate(cell):
    """Derive one observation using only its JSON cell and registered code."""
    payload = json.loads(cell) if isinstance(cell, str) else cell
    if payload.get('schema_version') != 1:
        raise ValueError('Unsupported payoff JSON schema.')
    weights = np.asarray([c['weight'] for c in payload['components']], dtype=float)
    if (weights < 0).any() or not np.isclose(weights.sum(), 1, atol=1e-12, rtol=0):
        raise ValueError('Observation component weights must sum to one.')
    rows = [calculate_record(dumps(payload['payoffs'][c['payoff_id']])) for c in payload['components']]
    values = {name: None if any(r[name] is None for r in rows) else float(np.dot(weights, [r[name] for r in rows]))
              for name in [*MEASURES, 'coded_number_of_compatible_issues']}
    return {**values, 'coverage': payload['coverage'],
            'input_issues': list(dict.fromkeys(note for p in payload['payoffs'].values()
                                               for note in p.get('input_issues', []))),
            'control_basis': list(dict.fromkeys(r['control_basis'] for r in rows)),
            'warnings': list(dict.fromkeys(note for r in rows for note in r['warnings']))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selected = parser.add_mutually_exclusive_group()
    selected.add_argument('--observation', help='Print the calculation for one observation ID.')
    selected.add_argument('--cell', type=Path, help='Calculate a copied JSON cell saved as a UTF-8 text file.')
    parser.add_argument('--check', action='store_true', help='Compare every JSON-derived value with the released columns.')
    parser.add_argument('--csv', type=Path, default=ROOT / 'data/regression_data.csv')
    args = parser.parse_args()
    if args.cell:
        if args.check:
            parser.error('--check compares CSV columns; use --cell alone for a copied cell.')
        print(json.dumps(calculate(args.cell.read_text(encoding='utf-8-sig')), indent=2, ensure_ascii=False))
        return
    csv.field_size_limit(10_000_000)
    with args.csv.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if args.observation:
        rows = [r for r in rows if r['observation_id'] == args.observation]
        if not rows:
            raise ValueError('Unknown observation ID.')
    mismatches, unavailable = [], []
    for row in rows:
        result = calculate(row[COLUMN])
        if args.observation or not args.check:
            print(json.dumps({'observation_id': row['observation_id'], **result}, indent=2, ensure_ascii=False))
        for name in MEASURES:
            if result[name] is None:
                unavailable.append({'observation_id': row['observation_id'], 'measure': name})
            elif not np.isclose(result[name], float(row[name]), atol=1e-12, rtol=0):
                mismatches.append({'observation_id': row['observation_id'], 'measure': name,
                                   'from_json': result[name], 'released_coding': float(row[name])})
    if args.check:
        matches = {name: len(rows) - sum(r['measure'] == name for r in mismatches + unavailable)
                   for name in MEASURES}
        print(json.dumps({'observations': len(rows), 'matching_released_values': matches,
                          'discrepancies': mismatches,
                          'unavailable_from_complete_payoffs': unavailable}, indent=2))
        if mismatches or unavailable:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
