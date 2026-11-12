# Study 1 replication materials

## Reproduce Study 1

**Main analysis dataset:** [data/regression_data.csv](data/regression_data.csv).

**Main Python analysis script:** [scripts/run.py](scripts/run.py). It loads the main dataset, prepares the comparison datasets, and produces the paper's tables, empirical figure, and robustness checks.

**Notebook version:** [scripts/analysis.ipynb](scripts/analysis.ipynb). Choose **Run all** to run the same analysis with short explanations.

[Download the complete Study 1 folder](https://github.com/SamQuinto/Search-Complexity/archive/refs/heads/main.zip), extract the ZIP, and open a terminal inside the extracted folder. With Python 3.12, run:

```bash
python -m pip install -r requirements.txt
python scripts/run.py
```

The code reproduces **Tables 1–3, Tables C1–C4, Figure 2, and the regression and robustness checks**. It includes the 5,000-draw resampling and single-observation omission checks. No account, API key, or original computer path is needed.

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
| [Regression data](data/regression_data.csv) | Main analysis values and a self-contained JSON payoff-input column |
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

- `data/`: coded sources, inventories, and analysis datasets. The intermediate comparison datasets in `data/derived/` are rebuilt by the main analysis.
- `scripts/`: start with [run.py](scripts/run.py). The notebook version is [analysis.ipynb](scripts/analysis.ipynb), and the [scripts README](scripts/README.md) explains both. Helper code is in `scripts/supporting/`.
- `results/`: current tables, Figure 2, and detailed statistical checks.
- `archive/`: earlier materials; these are not used by the replication and are omitted from the download ZIP.

The main replication reads the released analysis data. Add `--rebuild-data` to the command to recalculate the structural measures from the coded payoff and outcome sources before running the analyses. The workbooks and [data documentation](data/README.md) identify those sources and coding decisions. The papers and licensed teaching documents themselves are not redistributed here. Figure 1 is a conceptual illustration in the paper; Figure 2 is the empirical figure reproduced here.

## Calculate from the payoff column

`payoff_json`, immediately after `observation_id`, contains each observation's numerical payoff tables or functions, domains, reservation values or programmed acceptance rule, and component weights. Repeated tables use a lookup embedded inside the same cell. To calculate one observation or check all rows:

```bash
python scripts/supporting/payoff_info.py --observation SRU0286
python scripts/supporting/payoff_info.py --check
```

The helper checks both structural measures and all three counts for all 140 rows. Three Northcraft payoff records in one observation use valid source proofs and directly reported controls; their complete numerical schedules remain unavailable. [Input coverage](data/payoff_input_issues.csv) gives the observation, weights and missing material. Table options are paired by the same physical alternative across roles. Any control mismatch stops input preparation or the check command. See the [payoff-column notes](data/README.md#the-payoff-json-column) for the format and limitations.

Preregistration: https://osf.io/wtgxc
