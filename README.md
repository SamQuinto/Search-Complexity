# Search complexity and agreement in negotiations

Study 1 links observed agreement rates to the structure of scored, multi-issue negotiations. The main observation is an independent experiment or sample.

The current dataset contains **141 independent studies from 112 papers**, linked to 102 numerical negotiation structures and 66 recorded exercise names. Conditions within a study are combined. Independent studies using the same exercise retain separate agreement rates.

The revised analysis was run on 11 November 2026 after the author confirmed submission of the Study 1 OSF amendment. The amendment discloses the earlier study-level analyses of 5 November. Its public OSF link will be added when supplied. The [5 November release](https://github.com/SamQuinto/Search-Complexity/tree/2cfbb90ad56e38ea1eea6d9ecea2808df43c65bd) preserves the previous specification and results.

## Follow the data

| What you need | Where to look |
| --- | --- |
| Papers searched, recovery status and studies contributed | [Paper inventory](data/inventory/paper_inventory.csv) |
| Exercise names, sources and outcome coverage | [Exercise inventory](data/inventory/exercise_inventory.csv) |
| The fixed screening registry | [479 starting records](data/inventory/starting_study_registry.csv) |
| Study citations and paper identifiers | [Study-to-paper links](data/inventory/paper_study_links.csv) |
| Agreement evidence, structural sources and score calculations | [Coded inputs](data/sources/README.md) |
| One row per study with source information and controls | [Study inputs](data/study_inputs.csv) |
| Columns used by the regressions | [Regression data](data/regression_data.csv) |
| Read the saved model and robustness results | [Results](results.json) |
| Data construction and statistical decisions | [Study 1 methods](DATASET.md) |
| Reproduce the data, tables, figures and robustness checks | [Notebook](analysis.ipynb) |

The inventories document manual search and coding. The notebook joins the coded outcomes to structures, verifies the structural scores where replay inputs are available, and combines conditions within each study. It generates the flow and aggregation tables from the same records used for analysis.

## Reproduce Study 1

Download the repository ZIP and extract it. Open a terminal in that folder with Python 3.12 and run:

```bash
python -m pip install -r requirements.txt
python -m jupyter nbconvert --to notebook --execute analysis.ipynb --output analysis.executed.ipynb --ExecutePreprocessor.timeout=1800
```

You can also open `analysis.ipynb` and run all cells. The notebook uses the included inputs and writes to `outputs/`. It requires no account, key or private folder. The resampling checks use 5,000 draws.

If Jupyter is unavailable, `python analysis.py` runs the same steps and writes the same files.

`outputs/data_flow.csv` traces the sample. `outputs/component_weights.csv` documents each within-study weight. `outputs/metric_reproduction.csv` identifies the structures with replay inputs and the source-coded scores. `outputs/hypothesis_tests.csv`, `bootstrap_intervals.csv`, and `omission_checks.csv` report the inference and sensitivity checks. The notebook generates display-ready tables and both analytical figures.

## Results

H1 predicts a negative association between search complexity and agreement rates after accounting for bargaining-zone size and five controls. The estimate is −.112, with exercise-clustered p < .001 and a 95% interval of [−.139, −.085].

H2 compares explained variation using the same controls. R² is .424 for search complexity and .200 for bargaining-zone size. The difference is .225. Its primary exercise-resampling interval is [−.035, .398], so H2 is not supported by that test. The supplementary study-row interval is [.024, .386].

The supplementary structure comparison has 102 observations. Its stricter subset has 75. Both retain a negative adjusted search-complexity coefficient. H2's interval is positive in the 102-observation comparison and includes zero in the stricter subset. These comparisons combine the evidence differently and form separate analyses.

## Verification and source coverage

Three independent reviews checked the data and counts, model code, and manuscript. The data build reproduced all 141 study rows from a copy extracted to a different folder. The standalone metric check reproduces 32 coded structures, including 31 of the 102 linked to studies. Other structures use their recorded scores and source notes. An unexpected difference in a recalculated score stops the build for review.

The complete notebook ran in a relocated folder. Its dataset, models, resampling checks, journal tables and figures matched the Python script run. All 30 bootstrap interval records completed 5,000 draws with no invalid draws. Independent matrix calculations reproduced the main and weighted coefficients and clustered uncertainty.

The inventory retains historical retrieval flags and identifies unresolved screening. Of 370 candidate papers, 347 are marked recovered. This ledger flag is separate from study inclusion. The inventory README explains discrepancies and the limits of the screening records. Source papers and licensed teaching instructions remain in their respective libraries.
