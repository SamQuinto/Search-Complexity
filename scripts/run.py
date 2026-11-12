"""Run with: python -m scripts.run

Both this command and analysis.ipynb use the same procedure. Temporary working
files are removed automatically; only the current data and results are kept.
"""
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from .prepare_data import build_data
from .analysis import run_analysis
from .original_main_analysis import run_original_main
from .presentation import build_tables


def publish_files(root, working):
    """Keep datasets in data and statistical results in results."""
    files = {
        'regression_data.csv': 'data/regression_data.csv',
        'strict_regression_data.csv': 'data/strict_regression_data.csv',
        'data_flow.csv': 'data/data_flow.csv',
        'source_frequencies.csv': 'data/inventory/source_frequencies.csv',
        'tables.md': 'results/tables/README.md',
    }
    derived = ['study_inputs.csv', 'strict_study_inputs.csv', 'aggregate_main.csv',
               'aggregate_strict.csv', 'component_evidence.csv',
               'observation_eligibility.csv', 'payoff_metric_checks.csv',
               'catalog_component_metrics.csv', 'player_component_metrics.csv']
    files.update({name: 'data/derived/' + name for name in derived})
    checks = ['coefficients.csv', 'model_fit.csv', 'descriptive_statistics.csv',
              'correlations.csv', 'bootstrap_intervals.csv', 'leave_one_out.csv',
              'hypothesis_tests.csv', 'analysis_summary.json',
              'original_main_hypotheses.csv', 'original_main_bootstrap.csv',
              'original_main_omissions.csv', 'original_main_summary.json']
    files.update({name: 'results/checks/' + name for name in checks})
    for number in ['1', '2', '3', 'c1', 'c2', 'c3', 'c4']:
        name = 'table_' + number + '.csv'
        files[name] = 'results/tables/' + name
    files['figures/agreement_relationships.png'] = 'results/figures/figure_2.png'

    # Check before publishing, so a path or dependency problem cannot quietly
    # replace the released data with a different statistical sample.
    released = root / 'data/regression_data.csv'
    if released.exists():
        old = pd.read_csv(released).sort_values('observation_id').reset_index(drop=True)
        new = pd.read_csv(working / 'regression_data.csv').sort_values('observation_id').reset_index(drop=True)
        assert list(old.columns) == list(new.columns), 'The analysis columns changed.'
        assert old.observation_id.equals(new.observation_id), 'The observations changed.'
        np.testing.assert_allclose(old.iloc[:, 1:], new.iloc[:, 1:], atol=1e-12, rtol=0,
                                   equal_nan=True, err_msg='The rebuilt data differ from the released data.')
    for source, destination in files.items():
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(working / source, target)
    versions = {package: version(package) for package in
                ['numpy', 'pandas', 'scipy', 'statsmodels', 'matplotlib']}
    versions['python'] = sys.version.split()[0]
    (root / 'results/checks/software_versions.json').write_text(
        json.dumps(versions, indent=2) + '\n', encoding='utf-8')


def reproduce():
    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix='search-complexity-') as temporary:
        working = Path(temporary)
        print('Rebuilding the data and checking the payoff calculations...', flush=True)
        datasets = build_data(root, working)
        run_analysis(datasets, working, draws=5000)
        print('Running the original-registration appendix checks...', flush=True)
        run_original_main(root, working, draws=5000)
        build_tables(root, working)
        publish_files(root, working)
    print('Done. Data: data/. Tables, figure and checks: results/.', flush=True)
    return root / 'results'


if __name__ == '__main__':
    reproduce()
