# Run Study 1

Start with **[run.py](run.py)**, the main Python analysis script, and **[data/regression_data.csv](../data/regression_data.csv)**, the main analysis dataset. The script loads this dataset, prepares the intermediate comparison datasets, and produces the paper's tables, empirical figure, and robustness checks.

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

## Optional data reconstruction

From this folder, run `python run.py --rebuild-data` to also recalculate the structural measures from the coded payoff tables and outcome sources. This option then runs the same analyses. The regular command uses the released analysis dataset.

In the notebook, set `rebuild_from_coded_sources = True` for the same reconstruction.
