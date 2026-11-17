"""Compare the archival results using the number of local peaks."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.supporting import analysis
from scripts.supporting.payoff_info import calculate_record, dumps, input_records
from scripts.supporting.prepare_data import weights_for


def observation_counts(evidence, counts):
    rows = {}
    for observation, conditions in evidence.groupby('study_id', sort=False):
        values = conditions.payoff_id.map(counts)
        weights, *_ = weights_for(conditions)
        if values.isna().any():
            rows[observation] = np.nan
        else:
            rows[observation] = float(np.dot(weights, values))
    return rows


def compare(data, measure, dataset):
    is_count = measure == 'local_peak_count'
    sample = data.assign(search_complexity=data[measure])
    coefficients, fits = zip(*[
        analysis.fit(sample, model, peak_counts=is_count)
        for model in ('M1', 'M2', 'M3', 'M4', 'M5')
    ])
    seed = analysis.SEED + (dataset == 'strict')
    intervals = analysis.bootstrap(sample, 5000, seed, peak_counts=is_count)
    omissions, _ = analysis.leave_one_out(sample, peak_counts=is_count)
    results = analysis.confirmation_tests(
        pd.concat(coefficients), pd.DataFrame(fits), intervals, omissions, len(sample)
    ).assign(dataset=dataset, measure=measure)
    comparisons = pd.DataFrame(fits).set_index('model').r_squared
    return results.assign(r_squared_search=comparisons['M2'],
                          r_squared_bargaining_zone=comparisons['M5'])


def main():
    evidence = pd.read_csv(ROOT / 'data/derived/component_evidence.csv')
    records = input_records(ROOT)
    counts = {
        payoff_id: calculate_record(dumps(records[payoff_id]), local_peaks=True)['local_peak_count']
        for payoff_id in sorted(set(evidence.payoff_id))
    }
    output = ROOT / 'results' / 'local_peaks'
    output.mkdir(parents=True, exist_ok=True)
    pd.Series(counts, name='local_peak_count').rename_axis('payoff_id').to_csv(
        output / 'payoff_counts.csv'
    )
    tables = []
    for name, filename, conditions in (
        ('main', 'regression_data.csv', evidence),
        ('strict', 'strict_regression_data.csv', evidence.loc[evidence.strict_included]),
    ):
        data = pd.read_csv(ROOT / 'data' / filename, usecols=analysis.PREDICTORS
                           + ['observation_id', 'agreement_rate', 'negotiations'])
        data['local_peak_count'] = data.observation_id.map(observation_counts(conditions, counts))
        data[['observation_id', 'local_peak_count']].to_csv(
            output / f'{name}_observation_counts.csv', index=False
        )
        same_sample = data.dropna(subset=['local_peak_count'])
        print(f'{name}: {len(same_sample)} of {len(data)} observations with counts', flush=True)
        for measure in ['search_complexity', 'local_peak_count']:
            tables.append(compare(same_sample, measure, name))
    comparison = pd.concat(tables)
    comparison.to_csv(output / 'hypothesis_checks.csv', index=False)
    fields = ['dataset', 'measure', 'hypothesis', 'estimate', 'p',
              'bootstrap_ci_low', 'bootstrap_ci_high', 'omissions_passed']
    print(comparison[fields].to_string(index=False))


if __name__ == '__main__':
    main()
