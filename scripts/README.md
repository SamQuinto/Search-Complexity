# Run Study 1

Start with **[run.py](run.py)**, the main Python analysis script, and **[data/regression_data.csv](../data/regression_data.csv)**, the main analysis dataset. By default, the script rebuilds the coded primary inputs under `payoff > RV`, checks all five payoff-derived fields in every row, and produces the tables, Figure 2 and statistical checks.

The notebook version, **[analysis.ipynb](analysis.ipynb)**, runs the same analysis with short explanations. Choose **Run all** after installing the requirements below.

If your terminal is open in this `scripts` folder:

```bash
python -m pip install -r ../requirements.txt
python run.py
```

If your terminal is open in the repository's main folder:

```bash
python -m pip install -r requirements.txt
python -m scripts.run
```

Please use the [complete Study 1 download](https://github.com/SamQuinto/Search-Complexity/archive/refs/heads/main.zip), so this folder stays beside `data/` and `requirements.txt`. Python 3.12 and the pinned requirements were used for the replication check. No account, API key, or path edits are needed.

The main dataset is [regression_data.csv](../data/regression_data.csv). Rebuilt datasets go to [data](../data/), and tables, Figure 2, and statistical checks go to [results](../results/).

Both entry points also produce Table C5: one inclusive `>= RV` comparison, six source-bound cases and 123 point scenarios. Detailed results go to [results/reservation_rule](../results/reservation_rule/). The active inputs are 97 numerical records and three conditional Northcraft records; the source constraints and assumptions remain explicit.

## Supporting code

All helper code is in [supporting](supporting/). You do not need to run these files separately.

| File | Purpose |
| --- | --- |
| `prepare_data.py` | Check the coded evidence and combine conditions |
| `payoff_metrics.py` | Calculate bargaining-zone share and search complexity |
| `payoff_info.py` | Read one self-contained `payoff_json` cell or check the whole main dataset |
| `source_functions.py`, `additional_functions.py`, `sampled_metrics.py` | Apply the documented exercise-specific payoff calculations |
| `analysis.py` | Fit the regressions and run the robustness checks |
| `original_main_analysis.py` | Reproduce the original-registration appendix tests |
| `presentation.py` | Create the paper's tables, empirical figure, and data-flow counts |
| `reservation_sensitivity.py` | Recalculate the inclusive comparison and declared source-bound cases for Table C5 |

## Optional shortcuts

Use `python run.py --skip-reservations` for Tables 1–3 and C1–C4 with their main checks. `--use-released-data` loads the released primary dataset instead of rebuilding it; its payoff-cell checks still run. Neither option changes the primary `> RV` calculation.

In the Notebook, the corresponding switches are `check_reservations=False` and `rebuild_from_coded_sources=False`. Both default to `True`, so **Run all** follows the full Script workflow.
