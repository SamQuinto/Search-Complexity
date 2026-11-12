"""Reproduce the original registration's four main hypothesis tests.

This appendix uses the same source-corrected inputs as the current analyses,
but combines independent experiments using the same coded payoff record.
It applies the original full-sample, individual-row resampling and individual-
row omission criteria. It does not run the original supplementary analyses.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from .analysis import (SC, BZ, PREDICTORS, OUTCOME, complete_sample,
                      standardized_predictors, design, fit)


SEED = 20261113
MODELS = ['M1', 'M2', 'M3', 'M4', 'M5']
TESTS = {
    'H1': {'model': 'M4', 'term': BZ, 'direction': 1,
           'prediction': 'Larger bargaining-zone size predicts a higher agreement rate'},
    'H2': {'model': 'M1', 'term': SC, 'direction': -1,
           'prediction': 'Greater search complexity predicts a lower agreement rate'},
    'H3': {'model': 'M2 minus M5', 'term': 'r_squared_difference', 'direction': 1,
           'prediction': 'Search complexity and controls explain more variance than bargaining-zone size and controls'},
    'H4': {'model': 'M3', 'term': SC, 'direction': -1,
           'prediction': 'Search complexity predicts lower agreement rates after adding bargaining-zone size and controls'},
}


def ordinary_estimates(raw, y):
    """Fit all five models once for a paired bootstrap draw."""
    data = standardized_predictors(raw)
    total_variation = np.sum((y - y.mean()) ** 2)
    fitted = {}
    if total_variation <= 0:
        return {}
    for model in MODELS:
        try:
            x, terms, _ = design(data, model)
        except ValueError:
            continue
        if len(y) <= x.shape[1]:
            continue
        b = np.linalg.lstsq(x, y, rcond=None)[0]
        r_squared = 1 - np.sum((y - x @ b) ** 2) / total_variation
        fitted[model] = (dict(zip(terms, b)), r_squared)
    result = {}
    for hypothesis, rule in TESTS.items():
        if hypothesis == 'H3':
            if {'M2', 'M5'}.issubset(fitted):
                result[hypothesis] = fitted['M2'][1] - fitted['M5'][1]
        elif rule['model'] in fitted:
            result[hypothesis] = fitted[rule['model']][0][rule['term']]
    return result


def hypothesis_estimates(sample):
    """Use the same HC3/t convention as the five current regression models."""
    coefficients, fits = {}, {}
    for model in MODELS:
        coefficients[model], fits[model] = fit(sample, model)
    result = {}
    for hypothesis, rule in TESTS.items():
        if hypothesis == 'H3':
            estimate = fits['M2']['r_squared'] - fits['M5']['r_squared']
            result[hypothesis] = {
                'estimate': estimate, 'se': np.nan, 'p': np.nan,
                'ci_low': np.nan, 'ci_high': np.nan,
                'criterion_met': bool(estimate > 0),
            }
        else:
            row = coefficients[rule['model']].loc[
                coefficients[rule['model']].term.eq(rule['term'])].iloc[0]
            result[hypothesis] = {
                key: row[key] for key in ['b', 'se', 'p', 'ci_low', 'ci_high']}
            result[hypothesis]['estimate'] = result[hypothesis].pop('b')
            result[hypothesis]['criterion_met'] = bool(
                rule['direction'] * row.b > 0 and row.p < .05)
    return result, coefficients, fits


def run_original_main(root, output_dir=None, draws=5000):
    """Save the four original main tests and every required row-level check."""
    root = Path(root)
    output = root / 'outputs' if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data_path = output / 'aggregate_main.csv'
    if not data_path.exists():
        from .prepare_data import build_data
        build_data(root, output)
    sample = complete_sample(pd.read_csv(data_path))
    primary, coefficients, fits = hypothesis_estimates(sample)
    raw = sample[PREDICTORS].to_numpy(float)
    y = sample[OUTCOME].to_numpy(float)
    fast = ordinary_estimates(raw, y)
    for hypothesis in TESTS:
        np.testing.assert_allclose(primary[hypothesis]['estimate'], fast[hypothesis], atol=1e-10)

    # Resample entire coded payoff rows. The same selected rows enter all
    # models in a draw, so the R-squared comparison is paired.
    rng = np.random.default_rng(SEED)
    resampled = {hypothesis: [] for hypothesis in TESTS}
    for _ in range(draws):
        selected = rng.integers(0, len(sample), len(sample))
        estimates = ordinary_estimates(raw[selected], y[selected])
        for hypothesis, estimate in estimates.items():
            if np.isfinite(estimate):
                resampled[hypothesis].append(estimate)
    intervals = []
    for hypothesis, values in resampled.items():
        low, high = np.quantile(values, [.025, .975]) if values else [np.nan, np.nan]
        rule = TESTS[hypothesis]
        direction_pass = bool(low > 0) if rule['direction'] == 1 else bool(high < 0)
        intervals.append({
            'hypothesis': hypothesis, 'ci_low': low, 'ci_high': high,
            'draws_requested': draws, 'draws_completed': len(values),
            'invalid_draws': draws - len(values), 'seed': SEED,
            'criterion_met': bool(direction_pass and len(values) == draws),
        })
    intervals = pd.DataFrame(intervals).set_index('hypothesis')

    # The original confirmation rule requires every one-row omission to
    # retain the coefficient's predicted sign and p < .05 (or positive delta).
    omissions = []
    for observation_id in sample.observation_id:
        remaining = sample.loc[sample.observation_id.ne(observation_id)]
        try:
            estimates, _, _ = hypothesis_estimates(remaining)
            for hypothesis, estimate in estimates.items():
                omissions.append({
                    'hypothesis': hypothesis, 'omitted_payoff_id': observation_id,
                    'n': len(remaining), **estimate, 'error': '',
                })
        except ValueError as error:
            for hypothesis in TESTS:
                omissions.append({
                    'hypothesis': hypothesis, 'omitted_payoff_id': observation_id,
                    'n': len(remaining), 'criterion_met': False, 'error': str(error),
                })
    omissions = pd.DataFrame(omissions)

    results = []
    for hypothesis, rule in TESTS.items():
        omitted = omissions.loc[omissions.hypothesis.eq(hypothesis)]
        interval = intervals.loc[hypothesis]
        primary_test = primary[hypothesis]
        omission_pass = bool(len(omitted) == len(sample) and omitted.criterion_met.all())
        results.append({
            'hypothesis': hypothesis, 'prediction': rule['prediction'],
            'model': rule['model'], 'term': rule['term'], 'n': len(sample),
            **{f'primary_{key}': value for key, value in primary_test.items()},
            'bootstrap_ci_low': interval.ci_low, 'bootstrap_ci_high': interval.ci_high,
            'bootstrap_draws_completed': int(interval.draws_completed),
            'bootstrap_criterion_met': bool(interval.criterion_met),
            'omissions_passed': int(omitted.criterion_met.sum()),
            'omissions_required': len(sample), 'omission_criterion_met': omission_pass,
            'omission_estimate_min': omitted.estimate.min(),
            'omission_estimate_max': omitted.estimate.max(),
            'largest_omission_p': omitted.p.max(),
            'full_confirmation_met': bool(primary_test['criterion_met'] and
                                          interval.criterion_met and omission_pass),
        })
    results = pd.DataFrame(results)
    results.to_csv(output / 'original_main_hypotheses.csv', index=False)
    intervals.reset_index().to_csv(output / 'original_main_bootstrap.csv', index=False)
    omissions.to_csv(output / 'original_main_omissions.csv', index=False)
    summary = {
        'analysis': 'Original registration main hypothesis tests only',
        'n': len(sample),
        'unit': 'One coded payoff record, including any documented combination of payoff versions',
        'outcomes': 'Mean independent-experiment agreement rate within the coded payoff record',
        'source_corrections': 'The same final corrected sources as the current experiment-level analysis',
        'inference': 'HC3 standard errors with two-sided t tests; p < .05',
        'bootstrap': '5,000 individual coded-payoff-row draws, paired across models; 95% percentile intervals',
        'bootstrap_draws': draws, 'seed': SEED,
        'confirmation': 'The primary test, bootstrap interval and every individual-row omission must all pass',
        'original_supplementary_analyses_run': False,
        'r_squared': {model: float(value['r_squared']) for model, value in fits.items()},
        'hypotheses': results.replace({np.nan: None}).to_dict(orient='records'),
    }
    (output / 'original_main_summary.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return results
