# Search Complexity in Multi-Issue Negotiations

Does search complexity explain observed agreement rates beyond bargaining-zone size?
This repository contains the data and one notebook for the archival Study 1.

The audit dated 3 November 2026 retains 104 coded records. The main analysis uses
**103 observations from 67 named scenarios**. The stricter analysis uses
**75 observations from 54 named scenarios**. Excluded records and reasons remain visible.

## Reproduce the analysis

Use Python 3.12. Create and activate a virtual environment, then run:

```bash
python -m pip install -r requirements.txt
python -m jupyter nbconvert --to notebook --execute analysis.ipynb --output analysis.executed.ipynb --ExecutePreprocessor.timeout=1800
```

The notebook also opens in Jupyter or VS Code. Run its cells in order. It reads
only the included CSV files, requires no account or API key, and writes tables,
figures and all robustness results to the ignored outputs/ folder. Each
resampling check uses 5,000 draws. The recorded local analysis took about one minute;
runtime varies by computer.

## Files

- [analysis.ipynb](analysis.ipynb): methods, commented code, tables, figures and every specified robustness check.
- [data/search_complexity_dataset.csv](data/search_complexity_dataset.csv): all coded observations, variables, eligibility flags, outcomes and sources.
- [data/coding_evidence.csv](data/coding_evidence.csv): calculation methods, aggregation and coding decisions for each observation.
- [data/starting_study_registry.csv](data/starting_study_registry.csv): the fixed 479-study registry from 328 papers.
- [data/paper_inventory.csv](data/paper_inventory.csv): the paper list and recovery status after deduplication.
- [DATASET.md](DATASET.md): how the data were built and how to interpret the columns.

## Results and scope

The main sample meets the specified tests for H1-H4. In the stricter sample,
H2-H4 meet them; H1 does not. Supplementary checks are mixed and are reported individually.

This package reproduces analysis **from the coded dataset**. Rebuilding the
coding requires the original papers and teaching materials, which are not
redistributed. The audit independently recalculated the structural measures for
the nine included records with complete schedules and reservation values in the
compact archive. It does not claim independent structural reconstruction of every row.

The detailed plan is in the project's OSF preregistration materials folder.
The permanent registration URL and verified registration date must be supplied
before public release. This repository does not verify the chronology of
registration relative to earlier analyses.
The [Warsitzka et al. (2024) files](https://osf.io/2c9gf/) are a source dataset,
not this project's own registration.

The findings are observational and do not establish causality.
