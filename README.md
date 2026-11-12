# Study 1 replication materials

## Reproduce Study 1

[Download the complete Study 1 folder](https://github.com/SamQuinto/Search-Complexity/archive/refs/heads/main.zip), extract the ZIP, and open a terminal inside the extracted folder. With Python 3.12, run:

```bash
python -m pip install -r requirements.txt
python -m scripts.run
```

This rebuilds the analysis datasets from the coded sources, checks both structural measures, and reproduces **Tables 1–3, Tables C1–C4, Figure 2, and the regression and robustness checks**. It includes the 5,000-draw resampling and single-observation omission checks. No account, API key, or original computer path is needed.

You can also open [scripts/analysis.ipynb](scripts/analysis.ipynb) and choose **Run all** after installing the requirements. It runs the same code.

- **Use the final data:** [data/regression_data.csv](data/regression_data.csv). The stricter dataset is [data/strict_regression_data.csv](data/strict_regression_data.csv).
- **Read the reproduced tables:** [results/tables](results/tables/).
- **See the figure and detailed checks:** [results/figures](results/figures/) and [results/checks](results/checks/).

## Find what you need

| File | Contents |
| --- | --- |
| [Paper_inventory.xlsx](data/Paper_inventory.xlsx) | Papers, search sources, retrieval status, exercise matches, and contributions |
| [Observation_data.xlsx](data/Observation_data.xlsx) | Coded outcomes, payoff tables, reservation values, controls, and sources |
| [Raw payoff catalogue](data/raw_payoff_catalog.json) | Payoff tables and functions, reservation values, and calculation rules |
| [Regression data](data/regression_data.csv) | The minimal dataset used in the main analyses |
| [Exercise inventory](data/inventory/exercise_inventory.csv) | Negotiation exercises and material sources |
| [Starting registry](data/inventory/starting_study_registry.csv) | The original review records |
| [Record-to-observation links](data/inventory/registry_observation_links.csv) | How starting records contribute to the final observations |
| [Data flow](data/data_flow.csv) | Counts and the files supporting them |
| [Coding and calculations](data/README.md) | How the coded sources become the analysis data |
| [Combining conditions](data/derived/component_evidence.csv) | The source results and weights used for each observation |
| [Strict inclusion](data/derived/observation_eligibility.csv) | The decision and reason for each observation |
| [Metric checks](data/derived/payoff_metric_checks.csv) | Recalculation of the structural measures |
| [Approval rules](data/approval_rules.csv) | The agreement rule and its source for each payoff record |
| [Notebook](scripts/analysis.ipynb) | The complete replication, with short explanations |

## Folder guide

- `data/`: coded sources, inventories, and analysis datasets. `data/derived/` is rebuilt by the code.
- `scripts/`: start with [analysis.ipynb](scripts/analysis.ipynb) or [run.py](scripts/run.py). The [scripts README](scripts/README.md) explains both. Helper code is in `scripts/supporting/`.
- `results/`: current tables, Figure 2, and detailed statistical checks.
- `archive/`: earlier materials; these are not used by the replication and are omitted from the download ZIP.

The code begins with the numerical evidence transcribed from research papers and negotiation materials. The workbooks and [data documentation](data/README.md) identify those sources and coding decisions. The papers and licensed teaching documents themselves are not redistributed here. Figure 1 is a conceptual illustration in the paper; Figure 2 is the empirical figure reproduced here.

Preregistration: https://osf.io/wtgxc
