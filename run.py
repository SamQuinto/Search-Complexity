"""Rebuild the Study 1 data, analyses, tables and figures in one command."""

from pathlib import Path

from prepare_data import build_data
from analysis import run_analysis
from original_main_analysis import run_original_main
from presentation import build_tables


def reproduce():
    root = Path(__file__).resolve().parent
    output = root / 'outputs'
    datasets = build_data(root, output)
    run_analysis(datasets, output, draws=5000)
    run_original_main(root, output, draws=5000)
    build_tables(root, output)
    print('The replication files are in outputs/.')
    return output


if __name__ == '__main__':
    reproduce()
