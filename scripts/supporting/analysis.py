"""Fit Study 1 models and the planned checks using individual observations.

An observation is one independent experiment or recruited sample. Every
resampling draw selects whole observations. Conditions within an experiment
stay together because prepare_data.py has already combined them.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from .prepare_data import CONTROLS, PREDICTORS


SC = 'search_complexity'
BZ = 'bargaining_zone_share'
OUTCOME = 'agreement_rate'
MODELS = {
    'M1': [SC],
    'M2': [SC, *CONTROLS],
    'M3': [SC, BZ, *CONTROLS],
    'M4': [BZ],
    'M5': [BZ, *CONTROLS],
    'weighted_joint': [SC, BZ, *CONTROLS],
}
CONTINUOUS = [SC, BZ, *CONTROLS[:3]]
SEED = 20261111


def complete_sample(data, weighted=False):
    sample = data.dropna(subset=[OUTCOME, *PREDICTORS]).copy().reset_index(drop=True)
    if not sample.observation_id.is_unique:
        raise ValueError('Duplicate observation in the model data')
    if weighted:
        sample = sample.loc[sample.negotiations.notna() & sample.negotiations.gt(0) &
                            np.isfinite(sample.negotiations)].copy().reset_index(drop=True)
    if len(sample) < 3 or not sample[OUTCOME].between(0, 1).all():
        raise ValueError('Invalid or insufficient observed agreement data')
    if not sample[[SC, BZ, *CONTROLS[3:]]].apply(lambda x: x.between(0, 1)).all().all():
        raise ValueError('A proportion or indicator is outside its permitted range')
    if not (sample[SC] <= 1 - sample[BZ] + 1e-9).all():
        raise ValueError('Search complexity exceeds the unacceptable share of offers')
    return sample


def standardized_predictors(raw):
    data = np.array(raw, dtype=float, copy=True)
    for index, name in enumerate(PREDICTORS):
        if name in CONTINUOUS:
            sd = data[:, index].std()
            data[:, index] = (data[:, index] - data[:, index].mean()) / sd if sd > 1e-12 else 0
    return data


def design(data, model):
    """Keep estimable focal terms and omit constant or redundant controls."""
    names = ['const', *MODELS[model]]
    indices = [PREDICTORS.index(name) for name in MODELS[model]]
    matrix = np.column_stack([np.ones(len(data)), data[:, indices]])
    if np.linalg.matrix_rank(matrix) == matrix.shape[1]:
        return matrix, names, []
    keep, dropped = [0], []
    for index, name in enumerate(names[1:], start=1):
        if np.linalg.matrix_rank(matrix[:, [*keep, index]]) > len(keep):
            keep.append(index)
        elif name in [SC, BZ]:
            raise ValueError(f'{model}: {name} has no independent variation')
        else:
            dropped.append(name)
    return matrix[:, keep], [names[index] for index in keep], dropped


def fit(sample, model):
    """Report HC3 uncertainty, using a t reference with residual degrees of freedom."""
    weighted = model == 'weighted_joint'
    use = complete_sample(sample, weighted=weighted)
    matrix, terms, dropped = design(standardized_predictors(use[PREDICTORS]), model)
    x = pd.DataFrame(matrix, columns=terms)
    y = use[OUTCOME]
    if len(use) <= x.shape[1] or y.nunique() < 2:
        raise ValueError(f'{model}: insufficient residual variation')
    regression = sm.WLS(y, x, weights=use.negotiations) if weighted else sm.OLS(y, x)
    ordinary = regression.fit()

    # An indicator applying to just one observation fits that row perfectly.
    # Its HC3 uncertainty is undefined. Removing that row and its indicator
    # leaves the other coefficients and their HC3 uncertainty estimable.
    singleton = []
    absorbed = np.zeros(len(use), dtype=bool)
    for name in CONTROLS[3:]:
        if name in x and x[name].nunique() == 2:
            rare = x[name].map(x[name].value_counts()).eq(1).to_numpy()
            if rare.any():
                singleton.append(name)
                absorbed |= rare
    if singleton:
        reduced_x = x.loc[~absorbed].drop(columns=singleton)
        reduced_y = y.loc[~absorbed]
        reduced = sm.WLS(reduced_y, reduced_x, weights=use.negotiations.loc[~absorbed]) if weighted else sm.OLS(reduced_y, reduced_x)
        robust = reduced.fit(cov_type='HC3', use_t=True)
        np.testing.assert_allclose(robust.params, ordinary.params[reduced_x.columns], atol=1e-9)
    else:
        robust = regression.fit(cov_type='HC3', use_t=True)

    critical = stats.t.ppf(.975, ordinary.df_resid)
    coefficients = []
    for term, estimate in ordinary.params.items():
        se = robust.bse.get(term, np.nan)
        coefficients.append({
            'model': model, 'term': term, 'b': estimate, 'se': se,
            'p': 2 * stats.t.sf(abs(estimate / se), ordinary.df_resid) if se > 0 else np.nan,
            'ci_low': estimate - critical * se, 'ci_high': estimate + critical * se,
            'n': len(use), 'df_resid': ordinary.df_resid, 'uncertainty': 'HC3',
        })
    info = {'model': model, 'n': len(use), 'r_squared': ordinary.rsquared,
            'adjusted_r_squared': ordinary.rsquared_adj,
            'dropped_controls': ', '.join(dropped),
            'controls_with_unavailable_uncertainty': ', '.join(singleton),
            'predictions_below_zero': int((ordinary.fittedvalues < 0).sum()),
            'predictions_above_one': int((ordinary.fittedvalues > 1).sum())}
    return pd.DataFrame(coefficients), info


def fast_estimates(raw, y, weights=None):
    """Compute point estimates for a paired row-resampling draw."""
    data = standardized_predictors(raw)
    fit_models = ['weighted_joint'] if weights is not None else ['M2', 'M3', 'M5']
    weights = np.ones(len(y)) if weights is None else weights
    root_weights = np.sqrt(weights)
    total_variation = np.sum(weights * (y - np.average(y, weights=weights)) ** 2)
    results = {}
    for model in fit_models:
        try:
            x, names, _ = design(data, model)
        except ValueError:
            continue
        if len(y) <= x.shape[1] or total_variation <= 0:
            continue
        b = np.linalg.lstsq(x * root_weights[:, None], y * root_weights, rcond=None)[0]
        r_squared = 1 - np.sum(weights * (y - x @ b) ** 2) / total_variation
        results[model] = (dict(zip(names, b)), r_squared)
    output = {}
    if 'weighted_joint' in results:
        output['weighted_search_complexity'] = results['weighted_joint'][0][SC]
    if 'M3' in results:
        output['H1'] = results['M3'][0][SC]
    if {'M2', 'M5'}.issubset(results):
        output['H2'] = results['M2'][1] - results['M5'][1]
    return output


def bootstrap(sample, draws, seed, weighted=False):
    use = complete_sample(sample, weighted=weighted)
    raw, y = use[PREDICTORS].to_numpy(float), use[OUTCOME].to_numpy(float)
    weights = use.negotiations.to_numpy(float) if weighted else None
    tests = ['weighted_search_complexity'] if weighted else ['H1', 'H2']
    sampled = {name: [] for name in tests}
    rng = np.random.default_rng(seed)
    for _ in range(draws):
        positions = rng.integers(0, len(use), len(use))
        values = fast_estimates(raw[positions], y[positions],
                                None if weights is None else weights[positions])
        for name, value in values.items():
            if np.isfinite(value):
                sampled[name].append(value)
    rows = []
    for test, values in sampled.items():
        low, high = np.quantile(values, [.025, .975]) if values else (np.nan, np.nan)
        rows.append({'test': test, 'ci_low': low, 'ci_high': high,
                     'draws_requested': draws, 'draws_completed': len(values),
                     'invalid_draws': draws - len(values), 'seed': seed,
                     'n': len(use), 'weighted': weighted})
    return pd.DataFrame(rows)


def leave_one_out(sample, weighted=False):
    """Retain every other observation after omitting one experiment."""
    use = complete_sample(sample, weighted=weighted)
    rows, model_rows = [], []
    models = ['weighted_joint'] if weighted else ['M2', 'M3', 'M5']
    for observation in use.observation_id:
        remaining = use.loc[use.observation_id.ne(observation)]
        try:
            fits = {}
            for model in models:
                coefficient, info = fit(remaining, model)
                fits[model] = info
                model_rows.append(coefficient.assign(
                    omitted_observation=observation, weighted=weighted,
                    r_squared=info['r_squared']))
                if model == ('weighted_joint' if weighted else 'M3'):
                    sc = coefficient.loc[coefficient.term.eq(SC)].iloc[0]
            delta = fits['M2']['r_squared'] - fits['M5']['r_squared'] if not weighted else np.nan
            rows.append({'omitted_observation': observation, 'n': len(remaining),
                         'search_complexity_b': sc.b, 'search_complexity_p': sc.p,
                         'search_complexity_ci_low': sc.ci_low,
                         'search_complexity_ci_high': sc.ci_high,
                         'r_squared_difference': delta,
                         'negative_and_significant': bool(sc.b < 0 and sc.p < .05),
                         'weighted': weighted, 'error': ''})
        except ValueError as error:
            rows.append({'omitted_observation': observation, 'n': len(remaining),
                         'weighted': weighted, 'error': str(error)})
    return pd.DataFrame(rows), pd.concat(model_rows, ignore_index=True)


def descriptions(sample, dataset):
    variables = [OUTCOME, BZ, SC, *CONTROLS]
    summary = sample[variables].agg(['count', 'mean', 'std', 'min', 'max']).T
    summary.index.name = 'variable'
    pairs = []
    for i, left in enumerate(variables):
        for right in variables[i:]:
            r = p = np.nan
            if sample[left].nunique() > 1 and sample[right].nunique() > 1:
                r, p = stats.pearsonr(sample[left], sample[right])
            pairs.append({'dataset': dataset, 'variable': left,
                          'other_variable': right, 'r': r, 'p': p, 'n': len(sample)})
    return summary.reset_index().assign(dataset=dataset), pd.DataFrame(pairs)


def confirmation_tests(coefficients, fits, intervals, omissions, n):
    """Keep each required confirmation check visible instead of merging it silently.

    These checks matter because the final observation count depends on the
    archival evidence that can be recovered. A full-sample result alone is
    insufficient: its row-resampling interval and every row omission must pass.
    """
    joint = coefficients.loc[(coefficients.model == 'M3') &
                             (coefficients.term == SC)].iloc[0]
    fit_by_model = fits.set_index('model')
    delta = fit_by_model.loc['M2', 'r_squared'] - fit_by_model.loc['M5', 'r_squared']
    weighted_rows = omissions.weighted.astype(str).str.lower().isin(['true', '1', 'y']) if 'weighted' in omissions else None
    ordinary = omissions.loc[~weighted_rows].copy() if weighted_rows is not None else omissions.copy()
    valid = ordinary.error.fillna('').eq('')
    records = []
    for hypothesis in ['H1', 'H2']:
        interval = intervals.loc[intervals.test.eq(hypothesis)].iloc[0]
        if hypothesis == 'H1':
            primary_pass = bool(joint.b < 0 and joint.p < .05)
            bootstrap_pass = bool(interval.ci_high < 0)
            omission_pass = valid & ordinary.search_complexity_b.lt(0) & ordinary.search_complexity_p.lt(.05)
            estimate, se, p = joint.b, joint.se, joint.p
            low, high = joint.ci_low, joint.ci_high
            inference = 'HC3, two-sided t test; individual-observation confirmation checks'
        else:
            primary_pass = bool(delta > 0)
            bootstrap_pass = bool(interval.ci_low > 0)
            omission_pass = valid & ordinary.r_squared_difference.gt(0)
            estimate, se, p = delta, np.nan, np.nan
            low, high = interval.ci_low, interval.ci_high
            inference = 'Paired individual-observation interval and every individual-observation omission'
        # An incomplete set of planned draws or omissions cannot silently
        # count as full confirmation.
        bootstrap_pass = bool(bootstrap_pass and interval.draws_completed == interval.draws_requested)
        omissions_passed = int(omission_pass.sum())
        all_omissions_pass = bool(len(ordinary) == n and
                                 ordinary.omitted_observation.is_unique and omissions_passed == n)
        confirmed = bool(primary_pass and bootstrap_pass and all_omissions_pass)
        records.append({
            'hypothesis': hypothesis, 'estimate': estimate, 'se': se, 'p': p,
            'ci_low': low, 'ci_high': high,
            'primary_criterion_met': primary_pass,
            'bootstrap_ci_low': interval.ci_low, 'bootstrap_ci_high': interval.ci_high,
            'bootstrap_draws_requested': int(interval.draws_requested),
            'bootstrap_draws_completed': int(interval.draws_completed),
            'bootstrap_invalid_draws': int(interval.invalid_draws),
            'bootstrap_criterion_met': bootstrap_pass,
            'omissions_passed': omissions_passed, 'omissions_required': n,
            'omissions_completed': int(valid.sum()),
            'omission_criterion_met': all_omissions_pass,
            'full_confirmation_met': confirmed, 'criterion_met': confirmed,
            'inference': inference, 'n': n,
        })
    return pd.DataFrame(records)


def run_analysis(datasets, output_dir, draws=5000):
    """Run the five models and the checks specified for each observation unit."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {name: [] for name in ['coefficients', 'model_fit', 'descriptive_statistics',
                                   'correlations', 'bootstrap_intervals', 'leave_one_out',
                                   'leave_one_out_models', 'hypothesis_tests']}
    summary = {}
    for index, (name, raw) in enumerate(datasets.items()):
        sample = complete_sample(raw)
        print(f'{name}: {len(sample)} observations', flush=True)
        primary_unit = name in ['main', 'strict']
        models = list(MODELS) if primary_unit else [model for model in MODELS if model != 'weighted_joint']
        coefficients, fits = [], []
        for model in models:
            coef, info = fit(sample, model)
            coefficients.append(coef)
            fits.append(info)
        coefficients = pd.concat(coefficients, ignore_index=True)
        fits = pd.DataFrame(fits)
        tables['coefficients'].append(coefficients.assign(dataset=name))
        tables['model_fit'].append(fits.assign(dataset=name))
        descriptive, correlations = descriptions(sample, name)
        tables['descriptive_statistics'].append(descriptive)
        tables['correlations'].append(correlations)
        summary[name] = {'n': len(sample),
                         'weighted_n': len(complete_sample(sample, weighted=True)) if primary_unit else None}
        if not primary_unit:
            continue

        # The two comparison models share the same observations and controls.
        joint = coefficients.loc[(coefficients.model == 'M3') & (coefficients.term == SC)].iloc[0]
        fit_by_model = fits.set_index('model')
        delta = fit_by_model.loc['M2', 'r_squared'] - fit_by_model.loc['M5', 'r_squared']
        fast = fast_estimates(sample[PREDICTORS].to_numpy(float), sample[OUTCOME].to_numpy(float))
        np.testing.assert_allclose([joint.b, delta], [fast['H1'], fast['H2']], atol=1e-10)
        interval = bootstrap(sample, draws, SEED + index)
        tables['bootstrap_intervals'].append(interval.assign(dataset=name))
        tables['bootstrap_intervals'].append(bootstrap(sample, draws, SEED + index + 100,
                                                       weighted=True).assign(dataset=name))
        for weighted in [False, True]:
            omission, omission_models = leave_one_out(sample, weighted=weighted)
            tables['leave_one_out'].append(omission.assign(dataset=name))
            tables['leave_one_out_models'].append(omission_models.assign(dataset=name))
            if not weighted:
                ordinary_omissions = omission
        tables['hypothesis_tests'].append(
            confirmation_tests(coefficients, fits, interval, ordinary_omissions, len(sample))
            .assign(dataset=name, primary=name == 'main'))

    result = {name: pd.concat(parts, ignore_index=True) for name, parts in tables.items()}
    for name, table in result.items():
        table.to_csv(output_dir / f'{name}.csv', index=False, lineterminator='\n')
    (output_dir / 'analysis_summary.json').write_text(
        json.dumps({'bootstrap_draws': draws, 'base_seed': SEED, 'samples': summary}, indent=2),
        encoding='utf-8', newline='\n')
    return result
