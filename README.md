# Search complexity in negotiation · Replication materials

| Study | Where to start |
| --- | --- |
| **1. Agent-based model** | [Rebuild Figures 1 and 2 and replay the model](study1_agent_based_model/README.md) |
| **2. Archival analysis** | [Reproduce Study 2](#reproduce-study-2) |
| **3. Prolific experiment** | [Negotiation JSONs and post-task survey](study3_experiment/README.md) |

[Download the repository](https://github.com/SamQuinto/Search-Complexity/archive/refs/heads/main.zip), extract it, and install the requirements from the extracted folder using Python 3.12. The instructions for each study give its entry point.

## Reproduce Study 2

**Main analysis dataset:** [data/regression_data.csv](data/regression_data.csv).

**Main Python analysis script:** [scripts/run.py](scripts/run.py). It rebuilds the primary inputs, checks the payoff cells, and produces the paper's tables, empirical figure, and robustness checks.

**Notebook version:** [scripts/analysis.ipynb](scripts/analysis.ipynb). Choose **Run all** to run the same analysis with short explanations.

From the repository root, run:

```bash
python -m pip install -r requirements.txt
python scripts/run.py
```

The code reproduces the **archival tables, figure, regressions, and robustness checks**, including 5,000 resampling draws and checks that omit one observation at a time. It runs locally with the data in this repository.

Both the script and notebook rebuild the measures from the coded payoffs, using `payoff > RV`, and check the five values calculated from each payoff JSON cell. The [reservation-value checks](results/reservation_rule/) also test `>= RV` and other rules consistent with the available source information. Use `python scripts/run.py --skip-reservations`, or set `check_reservations=False` in the notebook, to skip those additional checks.

- **Use the final data:** [data/regression_data.csv](data/regression_data.csv). The stricter dataset is [data/strict_regression_data.csv](data/strict_regression_data.csv).
- **Read the reproduced tables:** [results/tables](results/tables/).
- **See the figure and detailed checks:** [results/figures](results/figures/) and [results/checks](results/checks/).
- **Reproduce the local peak check:** `python scripts/local_peaks.py`. See the [comparison and counts](results/local_peaks/README.md).

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
- `results/`: archival tables, figure, and statistical checks.
- `archive/`: earlier materials; these are not used by the replication and are omitted from the download ZIP.

Use `--use-released-data` to start from the released analysis dataset. The script still checks the measures against each payoff cell. The [data documentation](data/README.md) explains the sources and coding decisions recorded in the workbooks.

## Calculate from the payoff column

`payoff_json`, immediately after `observation_id`, contains each observation's numerical payoff tables or functions, domains, reservation values or programmed acceptance rule, and component weights. Repeated tables use a lookup embedded inside the same cell. To calculate one observation or check all rows:

```bash
python scripts/supporting/payoff_info.py --observation SRU0286
python scripts/supporting/payoff_info.py --check
```

The active catalogue contains 97 numerical payoff records and three Northcraft records using an explicit endpoint assumption and directly reported controls. Complete Northcraft schedules remain unavailable. The helper checks both structural measures and all three counts for every included row. [Input coverage](data/payoff_input_issues.csv) gives the observations, weights and missing material. Table options are paired by the same physical alternative across roles; any control mismatch stops preparation or checking. See the [payoff-column notes](data/README.md#the-payoff-json-column) for the format and limitations.

[Study 2 preregistration](https://osf.io/wtgxc)
