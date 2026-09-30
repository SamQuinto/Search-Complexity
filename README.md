# Search Complexity in Multi-Issue Negotiations

This repository contains the analysis-ready dataset and code for an archival study of agreement rates in scored, multi-issue negotiations.

The study asks whether search complexity predicts observed agreement rates beyond bargaining-zone size. Bargaining-zone size is the share of possible deals that every party would accept. Search complexity is the share of possible starting deals from which there is no path to the bargaining zone through one-issue changes that improve acceptance.

## Files

- [`data/search_complexity_dataset.csv`](data/search_complexity_dataset.csv): one row per matched negotiation version and observed agreement rate.
- [`analysis.ipynb`](analysis.ipynb): reproduces the descriptive statistics, Models 1-6, hypothesis tests, and robustness checks.
- [`DATASET.md`](DATASET.md): short explanation of how the dataset was built and what each group of columns means.

The current file contains 104 observations from 68 named negotiation scenarios. Eighty observations meet the stricter coding rules.

## Reproduce the analysis

```bash
python -m pip install numpy pandas jupyter
jupyter lab analysis.ipynb
```

Run the notebook from top to bottom. It reads only the CSV in this repository. The default setting uses 5,000 bootstrap draws, so the robustness section takes longer than the main regressions.

## Preregistration and source materials

The full inclusion, exclusion, source-priority, matching, aggregation, and ambiguity rules are documented in the project's **OSF preregistration materials** folder. The permanent public OSF registration URL should be added here when the registration is public.

Published papers, supplementary files, and proprietary teaching scenarios are not redistributed in this repository. The CSV records the source used for each payoff structure and agreement rate so that the coding can be audited against legally obtained source materials.

This is an observational archival study. The results describe associations and do not by themselves establish causality.
