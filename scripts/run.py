"""Run with: python -m scripts.run

Both this command and analysis.ipynb use the same procedure. Temporary working
files are removed automatically; only the current data and results are kept.
"""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

# Support both the repository command and running run.py from this folder.
REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from scripts.supporting.prepare_data import MODEL_COLUMNS, build_data, prepare_analysis_data
from scripts.supporting.analysis import run_analysis
from scripts.supporting.original_main_analysis import run_original_main
from scripts.supporting.presentation import build_tables
from scripts.supporting.payoff_info import check_payoff_columns


def publish_files(root, working):
    """Keep datasets in data and statistical results in results."""
    files = {
        'regression_data.csv': 'data/regression_data.csv',
        'strict_regression_data.csv': 'data/strict_regression_data.csv',
        'data_flow.csv': 'data/data_flow.csv',
        'source_frequencies.csv': 'data/inventory/source_frequencies.csv',
        'tables.md': 'results/tables/README.md',
        'tables.json': 'results/tables/tables.json',
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
        np.testing.assert_allclose(old[MODEL_COLUMNS[1:]], new[MODEL_COLUMNS[1:]], atol=1e-12, rtol=0,
                                   equal_nan=True, err_msg='The rebuilt data differ from the released data.')
    optional = {'payoff_metric_checks.csv', 'catalog_component_metrics.csv', 'player_component_metrics.csv'}
    for source, destination in files.items():
        if source in optional and not (working / source).exists():
            continue
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(working / source, target)
    versions = {package: version(package) for package in
                ['numpy', 'pandas', 'scipy', 'statsmodels', 'matplotlib']}
    versions['python'] = sys.version.split()[0]
    (root / 'results/checks/software_versions.json').write_text(
        json.dumps(versions, indent=2) + '\n', encoding='utf-8', newline='\n')


def reproduce(rebuild_data=True, check_reservations=True):
    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix='search-complexity-') as temporary:
        working = Path(temporary)
        if rebuild_data:
            print('Rebuilding from the coded payoff and outcome sources...', flush=True)
            datasets = build_data(root, working)
        else:
            print('Loading data/regression_data.csv and preparing the comparison datasets...', flush=True)
            datasets = prepare_analysis_data(root, working)
        check_payoff_columns(pd.read_csv(working / 'regression_data.csv'))
        run_analysis(datasets, working, draws=5000)
        print('Running the original-registration appendix checks...', flush=True)
        run_original_main(root, working, draws=5000)
        build_tables(root, working)
        publish_files(root, working)
        if check_reservations:
            from scripts.supporting.reservation_sensitivity import run_reservation_sensitivity
            run_reservation_sensitivity(root)
    print('Done. Data: data/. Tables, figure and checks: results/.', flush=True)
    return root / 'results'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild-data', action='store_true', default=True,
                        help='Also reconstruct the analysis data from the coded payoff and outcome sources.')
    parser.add_argument('--use-released-data', dest='rebuild_data', action='store_false',
                        help='Load the released primary dataset instead of rebuilding it; still check its payoff cells.')
    parser.add_argument('--skip-reservations', action='store_true',
                        help='Run Tables 1–3 and C1–C4 without recalculating the reservation-boundary checks.')
    args = parser.parse_args()
    reproduce(rebuild_data=args.rebuild_data, check_reservations=not args.skip_reservations)
