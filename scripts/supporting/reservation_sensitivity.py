"""Check Study 1's > RV primary rule against >= RV and source-bound scenarios.

The rule comparison changes only the numeric acceptance comparison; coded RVs,
payoffs, outcomes, controls, approval quotas, grids, seeds and programmed
nonnumeric classifiers stay fixed. Separate source-bound cases vary the declared
Beersma allocation weights and Northcraft endpoint inferences.
Six > cases cross feasible Beersma allocation endpoints with Northcraft's
conditional endpoint and common bounds; all 123 feasible point cases are checked.
One additional full case uses the inclusive >= numeric comparison.
"""
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
import pandas as pd

from . import payoff_metrics as payoff
from .source_functions import calculate_formula_inputs
from .additional_functions import calculate_additional_inputs
from .sampled_metrics import calculate_player_input
from .prepare_data import (MODEL_COLUMNS, PREDICTORS, combine_study_components,
                           aggregate_identical_structures)
from .analysis import run_analysis, fit, fast_estimates
from .original_main_analysis import run_original_main, hypothesis_estimates

MEASURES = ['search_complexity', 'bargaining_zone_share']
BEERSMA = 'beersma_de_dreu_2002_market_four_versions_pooled'
NC_PREFIX = 'northcraft_1998_employment_'
CASES = [('inclusive_ge', None, None)] + [(f'{nc}_x{x}', nc, x)
         for nc in ('endpoint', 'lower', 'upper') for x in (4, 44)]


def _weights(x):
    if not isinstance(x, int) or not 4 <= x <= 44:
        raise ValueError('The source-feasible Beersma allocation is integer x=4..44.')
    counts = np.array([x, 47 - x, 46 - x, x - 2])
    assert counts.sum() == 91 and (counts >= 2).all()
    return counts / 91


def _source_hashes(root):
    paths = [root / 'data' / name for name in ['raw_payoff_catalog.json', 'acceptability_proofs.json',
             'programmed_acceptance_rules.json', 'within_payoff_weights.csv', 'component_decisions.csv',
             'reservation_rule_sources.json', 'sources/study_outcomes.csv', 'sources/structure_inputs.csv',
             'sources/structural_scores.csv', 'sources/metric_input_manifest.csv', 'sources/acceptance_inputs.npz',
             'derived/component_evidence.csv', 'regression_data.csv']]
    paths += sorted((root / 'data/payoff_schedules').glob('*.json'))
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}


def calculate_source_metrics(root, strict=True):
    """Recalculate every active structural record, without changing source files."""
    root = Path(root)
    structures = pd.read_csv(root / 'data/sources/structure_inputs.csv').rename(columns={'observation_id': 'payoff_id'})
    values, parts = payoff.calculate_catalog_inputs(root / 'data/raw_payoff_catalog.json', structures,
        root / 'data/within_payoff_weights.csv', strict=strict,
        component_weights=None)
    records = list(values)
    records += [payoff.calculate_payoff_file(p, strict) for p in sorted((root / 'data/payoff_schedules').glob('*.json'))]
    records += payoff.calculate_programmed_rules(root / 'data/programmed_acceptance_rules.json', strict)
    records += calculate_formula_inputs(root, strict) + calculate_additional_inputs(root, strict)
    player, _ = calculate_player_input(root / 'data/raw_payoff_catalog.json', strict)
    records.append(player)
    records += payoff.calculate_acceptability_proofs(root / 'data/acceptability_proofs.json', strict)
    lookup, provenance = {}, {}
    for record in records:
        key = record['payoff_id']
        if key in lookup:
            for measure in MEASURES:
                np.testing.assert_allclose(lookup[key][measure], record[measure], rtol=0, atol=1e-12)
        lookup[key] = record
        provenance.setdefault(key, []).append(record.get('input_type', ''))
    catalog = json.loads((root / 'data/raw_payoff_catalog.json').read_text(encoding='utf-8'))
    if set(lookup) != {row['payoff_id'] for row in catalog}:
        raise ValueError('Every active payoff record needs a complete numerical calculation or explicit source proof.')
    manifest = pd.read_csv(root / 'data/sources/metric_input_manifest.csv')
    if not set(manifest.payoff_id).issubset({row['payoff_id'] for row in values}):
        raise ValueError('An acceptance-grid record lacks its underlying numerical reconstruction.')
    frame = pd.DataFrame([{**row, 'calculation_sources': ' | '.join(provenance[key])}
                          for key, row in lookup.items()]).set_index('payoff_id')
    return frame, parts, catalog


def _datasets(components, metrics):
    frame = components.copy()
    for measure in MEASURES:
        frame[measure] = frame.payoff_id.map(metrics[measure])
    if frame[MEASURES].isna().any().any():
        raise ValueError('An included component has unidentified structural metrics.')
    strict = frame.loc[frame.strict_included].copy()
    return {'main': combine_study_components(frame), 'strict': combine_study_components(strict),
            'aggregate_main': aggregate_identical_structures(frame),
            'aggregate_strict': aggregate_identical_structures(strict)}


def _scenario(base, parts, catalog, northcraft, x, sources):
    metrics = base.copy()
    names = [p['component'] for p in next(e for e in catalog if e['payoff_id'] == BEERSMA)['components']]
    selected = parts.loc[parts.payoff_id.eq(BEERSMA)].set_index('component').loc[names]
    for measure in MEASURES:
        metrics.loc[BEERSMA, measure] = float(np.dot(_weights(x), selected[measure]))
    cfg = sources['northcraft']
    zone = {'endpoint': cfg['strict_bargaining_zone_share_conditional_on_unique_zero_endpoints'],
            'lower': cfg['strict_bargaining_zone_conservative_bounds_without_endpoint_condition'][0],
            'upper': cfg['strict_bargaining_zone_conservative_bounds_without_endpoint_condition'][1]}[northcraft]
    metrics.loc[metrics.index.str.startswith(NC_PREFIX), 'bargaining_zone_share'] = zone
    return metrics


def _point_checks(datasets):
    rows = []
    for name in ('main', 'strict'):
        sample = datasets[name]
        coefficients, _ = fit(sample, 'M3')
        sc = coefficients.loc[coefficients.term.eq('search_complexity')].iloc[0]
        delta = fast_estimates(sample[PREDICTORS].to_numpy(float), sample.agreement_rate.to_numpy(float))['H2']
        rows += [{'dataset': name, 'hypothesis': 'H1', 'estimate': sc.b, 'p': sc.p,
                  'point_criterion_met': bool(sc.b < 0 and sc.p < .05)},
                 {'dataset': name, 'hypothesis': 'H2', 'estimate': delta, 'p': np.nan,
                  'point_criterion_met': bool(delta > 0)}]
    original, _, _ = hypothesis_estimates(datasets['aggregate_main'])
    rows += [{'dataset': 'original_registration', 'hypothesis': key, 'estimate': result['estimate'],
              'p': result['p'], 'point_criterion_met': result['criterion_met']} for key, result in original.items()]
    return rows


def _summary(case, path):
    h = pd.read_csv(path / 'hypothesis_tests.csv')
    original = pd.read_csv(path / 'original_main_hypotheses.csv')
    rows = []
    for name in ('main', 'strict'):
        a = h.loc[h.dataset.eq(name)].set_index('hypothesis')
        one, two = a.loc['H1'], a.loc['H2']
        rows.append({'case': case, 'sample': name, 'n': int(one.n), 'SC_b': one.estimate, 'SC_p': one.p,
            'SC_bootstrap_low': one.bootstrap_ci_low, 'SC_bootstrap_high': one.bootstrap_ci_high,
            'delta_R2': two.estimate, 'delta_bootstrap_low': two.bootstrap_ci_low,
            'delta_bootstrap_high': two.bootstrap_ci_high,
            'current_full_confirmation': bool(a.full_confirmation_met.all()),
            'original_full_confirmation': bool(original.full_confirmation_met.all())})
    return rows


def _write_table(root, rows):
    comparison = pd.DataFrame(rows)
    comparison.to_csv(root / 'results/reservation_rule/comparison.csv', index=False, lineterminator='\n')
    table = comparison[['case', 'sample', 'n', 'current_full_confirmation', 'original_full_confirmation']].copy()
    table['SC b [bootstrap CI]'] = comparison.apply(lambda r: f'{r.SC_b:.4f} [{r.SC_bootstrap_low:.4f}, {r.SC_bootstrap_high:.4f}]', axis=1)
    table['R2 difference [bootstrap CI]'] = comparison.apply(lambda r: f'{r.delta_R2:.4f} [{r.delta_bootstrap_low:.4f}, {r.delta_bootstrap_high:.4f}]', axis=1)
    table = table[['case', 'sample', 'n', 'SC b [bootstrap CI]', 'R2 difference [bootstrap CI]',
                   'current_full_confirmation', 'original_full_confirmation']]
    table.to_csv(root / 'results/tables/table_c5.csv', index=False, lineterminator='\n')
    readme = root / 'results/tables/README.md'
    text = readme.read_text(encoding='utf-8') if readme.exists() else ''
    text = text.split('\n## Table C5')[0]
    columns = list(table.columns)
    lines = ['\n## Table C5. Reservation-boundary checks\n',
             'The primary rule is > RV; inclusive_ge uses >= RV. Sample strict denotes the evidence-restricted sample. Full confirmation includes the same 5,000 draws and required omissions. '
             'Northcraft endpoints are conditional source inferences; lower/upper cases use common source bounds. '
             'Beersma x4/x44 preserve the recovered marginals and populated cells. All 123 point cases are in results/reservation_rule/; six cases receive full resampling.\n',
             '| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    lines += ['| ' + ' | '.join(str(row[c]) for c in columns) + ' |' for row in table.to_dict('records')]
    readme.write_text(text + '\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def run_reservation_sensitivity(root, output_dir=None, draws=5000):
    """Write the inclusive check, six > bound checks and 123 > point scenarios."""
    root = Path(root)
    output = root / 'results/reservation_rule' if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sources = json.loads((root / 'data/reservation_rule_sources.json').read_text(encoding='utf-8'))
    before = _source_hashes(root)
    weak, _, _ = calculate_source_metrics(root, strict=False)
    strong, parts, catalog = calculate_source_metrics(root, strict=True)
    components = pd.read_csv(root / 'data/derived/component_evidence.csv')
    baseline = _datasets(components, strong)
    released = pd.read_csv(root / 'data/regression_data.csv')
    expected = released[MODEL_COLUMNS].sort_values('observation_id').reset_index(drop=True)
    actual = baseline['main'][MODEL_COLUMNS].sort_values('observation_id').reset_index(drop=True)
    assert expected.observation_id.equals(actual.observation_id)
    np.testing.assert_allclose(expected.iloc[:, 1:], actual.iloc[:, 1:], atol=1e-12, rtol=0, equal_nan=True)
    structures = [strong.reset_index().assign(case='primary_gt')]
    rows = _summary('primary_gt', root / 'results/checks')
    base_coefficients = pd.read_csv(root / 'results/checks/coefficients.csv')
    crossings = []
    for case, nc, x in CASES:
        print(f'Reservation rule: {case}', flush=True)
        metrics = weak if case == 'inclusive_ge' else _scenario(strong, parts, catalog, nc, x, sources)
        datasets = _datasets(components, metrics)
        path = output / case
        path.mkdir(exist_ok=True)
        for name, frame in datasets.items():
            frame[[column for column in MODEL_COLUMNS if column in frame]].to_csv(path / f'{name}.csv', index=False, lineterminator='\n')
        run_analysis(datasets, path, draws=draws)
        run_original_main(root, path, draws=draws)
        rows += _summary(case, path)
        structures.append(metrics.reset_index().assign(case=case))
        coefficients = pd.read_csv(path / 'coefficients.csv')
        joined = base_coefficients.merge(coefficients, on=['dataset', 'model', 'term'], suffixes=('_primary', '_strict'), validate='one_to_one')
        changed = joined.loc[(joined.p_primary < .05) != (joined.p_strict < .05)]
        crossings.append(changed.assign(case=case))
    pd.concat(structures, ignore_index=True).to_csv(output / 'structural_metrics.csv', index=False, lineterminator='\n')
    pd.concat(crossings, ignore_index=True).to_csv(output / 'secondary_significance_changes.csv', index=False, lineterminator='\n')
    grid = []
    for nc in ('endpoint', 'lower', 'upper'):
        for x in range(4, 45):
            datasets = _datasets(components, _scenario(strong, parts, catalog, nc, x, sources))
            grid += [{**row, 'northcraft': nc, 'beersma_x': x} for row in _point_checks(datasets)]
    pd.DataFrame(grid).to_csv(output / 'point_scenarios.csv', index=False, lineterminator='\n')
    pd.DataFrame(rows).to_csv(output / 'comparison.csv', index=False, lineterminator='\n')
    code = [Path(__file__), Path(payoff.__file__), Path(__file__).with_name('source_functions.py'),
            Path(__file__).with_name('additional_functions.py'), Path(__file__).with_name('sampled_metrics.py'),
            Path(__file__).with_name('analysis.py'), Path(__file__).with_name('original_main_analysis.py')]
    provenance = {'source_sha256': before, 'active_structures': len(weak),
        'code_sha256': {p.name: sha256(p.read_bytes()).hexdigest() for p in code if p.exists()},
        'sample_sizes': {name: len(frame) for name, frame in baseline.items()},
        'source_data_unchanged': before == _source_hashes(root), 'draws_per_full_case': draws,
        'full_cases': [{'case': c, 'northcraft': n, 'beersma_x': x} for c, n, x in CASES],
        'point_cases': 123, 'coverage': sources['coverage'], 'source_constraints': sources}
    if not provenance['source_data_unchanged']:
        raise ValueError('A coded source changed during the sensitivity run.')
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8', newline='\n')
    # The public entry points use the standard output location and add Table C5.
    if output == root / 'results/reservation_rule':
        _write_table(root, rows)
    print('Reservation-rule checks complete: inclusive case, six > bound cases and 123 point scenarios.', flush=True)
    return pd.DataFrame(rows)
