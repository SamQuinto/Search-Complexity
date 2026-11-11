# Search complexity and agreement in negotiations

Study 1 asks whether search complexity predicts agreement rates beyond bargaining-zone size and other structural features of a negotiation exercise.

The dataset contains **141 observations from 112 papers**, linked to **103 payoff records across 66 named negotiation exercises**. An observation is an experiment or separately recruited participant sample. Conditions within an experiment are combined; independent experiments using the same exercise remain separate. The strict analysis retains **126 observations**.

## Find what you need

| File | Contents |
| --- | --- |
| [Paper_inventory.xlsx](data/Paper_inventory.xlsx) | The 371 papers, how they were found, retrieval status, exercise matches, and observations contributed |
| [Observation_data.xlsx](data/Observation_data.xlsx) | Agreement outcomes, underlying results, payoff tables or functions, reservation values, controls, and sources, before adding the two structural measures |
| [Regression data](data/regression_data.csv) | The 141 observations and ten columns used by the analysis |
| [Exercise inventory](data/inventory/exercise_inventory.csv) | The 66 exercises, material sources, and contributions |
| [Starting registry](data/inventory/starting_study_registry.csv) | The fixed 479 review records, linked to 330 papers |
| [Counts and units](data/data_flow.csv) | The search, recovered papers, coded results, and final analysis observations |
| [Data collection and calculations](DATASET.md) | Inclusion, source priorities, combining conditions, structural measures, and statistical tests |
| [Tables](Tables.md) | Descriptive statistics, five main regressions, strict results, and supplementary checks |
| [Notebook](analysis.ipynb) | Rebuild the data and reproduce the results |

We read the papers and research materials to code the evidence. The notebook starts from those transcriptions, checks the structural calculations, combines conditions within observations, and creates the regression data. Sources and coding decisions remain attached to the underlying results.

## Run the analysis

Download this folder, extract it, and open a terminal in the extracted folder. With Python 3.12, run:

```bash
python -m pip install -r requirements.txt
python run.py
```

Or open `analysis.ipynb` and choose **Run all** after installing the requirements. Everything is saved in `outputs/`. The code uses relative paths and needs no account or API key. Each resampling check uses 5,000 draws with a fixed seed.

## Main findings

In the joint model, greater search complexity is associated with lower agreement rates (**b = −.109, p < .001**). Its model with controls explains more variation than the bargaining-zone model with the same controls (**ΔR² = .206; 95% interval [.025, .361]**). Both hypotheses meet their main regression, individual-observation resampling, and single-observation omission criteria.

The notebook also reproduces the original main hypothesis analyses in Appendix A, using `original_main_analysis.py`.

The workbook and source files provide numerical transcriptions and citations. Research papers and proprietary teaching documents remain in their respective libraries.
