# Search complexity and agreement in negotiations

Does search complexity explain agreement rates beyond bargaining-zone size?
This repository contains the coded Study 1 data and one replication notebook.

The primary analysis uses **141 empirical studies from 112 papers**, linked to
66 recorded scenario names. Each experiment or independent sample is one
observation. Independent studies using the same scenario remain separate.
Conditions or repeated tasks within a study are combined.

## Reproduce

Use Python 3.12 in a virtual environment. From this folder, run:

```bash
python -m pip install -r requirements.txt
python -m jupyter nbconvert --to notebook --execute analysis.ipynb --output analysis.executed.ipynb --ExecutePreprocessor.timeout=1800
```

Or open `analysis.ipynb` in Jupyter or VS Code and run all cells. It first
rebuilds the study data from the source-outcome crosswalk, then runs all six
models and checks. Each bootstrap uses 5,000 draws. It takes a few minutes and
requires no account, API key or private path. Results go in `outputs/`.

## Files

- [analysis.ipynb](analysis.ipynb): commented reconstruction, analysis and figures.
- [data/study_level_dataset.csv](data/study_level_dataset.csv): the 141 main observations.
- [data/study_outcomes.csv](data/study_outcomes.csv): 169 components linking study outcomes to structures.
- [data/search_complexity_dataset.csv](data/search_complexity_dataset.csv): earlier structural aggregation; 103 included rows, 75 in its stricter subset.
- [data/coding_evidence.csv](data/coding_evidence.csv): structural calculations and decisions.
- [data/starting_study_registry.csv](data/starting_study_registry.csv): the fixed 479-study registry.
- [data/paper_inventory.csv](data/paper_inventory.csv): the deduplicated search list.
- [DATASET.md](DATASET.md): coding and aggregation rules.

## Interpretation

The study-level analysis meets the stated tests for H2-H4; H1 is not supported.
The earlier structural aggregation supports H1-H4; its stricter subset supports
H2-H4. Supplementary checks are mixed, including nonsignificant rank correlations.
The notebook reports every result.

The primary unit is an analytical revision dated 5 November 2026. The archived
plan used the earlier structural aggregation. Do not describe the new unit as
the original preregistered specification. The permanent OSF registration URL
and verified submission date must be supplied before public release.
[Warsitzka et al. (2024)](https://osf.io/2c9gf/) provide a source dataset;
that link is not this project's registration.

This package reproduces analysis and source-outcome aggregation from coded files.
It does not independently recreate every payoff calculation from the papers.
Nine complete included schedules were recalculated in the previous audit.
Licensed papers, teaching materials and credentials are not redistributed.
The findings are observational.
