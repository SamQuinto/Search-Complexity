# Search complexity and agreement in negotiations

Does search complexity explain agreement rates beyond bargaining-zone size?
This repository contains the Study 1 data, its sources and one replication notebook.

The current analysis includes **141 studies from 112 papers**. Each independent
experiment or sample contributes one observation. Studies using the same scenario
remain separate; conditions within a study are combined.

## Start here

| What you need | File |
| --- | --- |
| How we collected, coded and combined the evidence | [DATASET.md](DATASET.md) |
| Final dataset used in the main analysis | [study_level_dataset.csv](data/study_level_dataset.csv) |
| Rebuild the final dataset and reproduce the analyses | [analysis.ipynb](analysis.ipynb) |
| Read the existing results without running anything | [results.json](results.json) |
| Papers searched and whether they were recovered | [paper_inventory.csv](data/search/paper_inventory.csv) |
| The 479 starting study records | [starting_study_registry.csv](data/search/starting_study_registry.csv) |
| Outcomes linked to the coded structures | [study_outcomes.csv](data/sources/study_outcomes.csv) |
| Structural scores and inclusion decisions | [structures.csv](data/sources/structures.csv) |
| Source evidence, calculation methods and coding notes | [coding_evidence.csv](data/sources/coding_evidence.csv) |

The sequence is: identify papers → read and code sources → match outcomes to
structures → combine conditions within studies → analyse the final dataset.
Source coding is documented in the CSVs and [DATASET.md](DATASET.md). The notebook
rebuilds the final dataset from those coded records; it does not automatically
extract payoff tables from papers or recalculate every structural score.

## Run the notebook

Use Python 3.12. In this folder, install the listed packages and run:

```bash
python -m pip install -r requirements.txt
python -m jupyter nbconvert --to notebook --execute analysis.ipynb --output analysis.executed.ipynb --ExecutePreprocessor.timeout=1800
```

Or open `analysis.ipynb` in Jupyter or VS Code and run its cells in order.
No API key, account or private folder is needed. Results are written to `outputs/`.
The 5,000-draw checks take a few minutes. Package versions are in
[requirements.txt](requirements.txt).

## Reading the results

The 5 November 2026 study-level analysis supports H2–H4 under the stated
observation-based tests; H1 is not supported. Supplementary checks are mixed.
The notebook also reports the earlier 103-observation structural aggregation
and its 75-observation stricter subset. These are different ways of combining
the evidence, not additional studies to append to the main sample.

The study-level unit is a dated change from the archived preregistration.
The public registration link still needs to be added. The
[Warsitzka et al. (2024) source repository](https://osf.io/2c9gf/) is a data source,
not our registration. Papers, licensed teaching materials and credentials are
not included. These findings describe associations.

Older public files are preserved in [archive/](archive/README.md) and Git history.
They are not used by the current notebook and are excluded from Git source ZIPs.
