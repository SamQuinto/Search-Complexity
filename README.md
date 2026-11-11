# Search complexity and agreement in negotiations

Study 1 asks whether search complexity predicts agreement rates beyond bargaining-zone size and other structural features of a negotiation exercise.

Preregistration: https://osf.io/wtgxc

The dataset contains **141 observations from 112 papers**, linked to **103 payoff records across 66 named negotiation exercises**. An observation is an experiment or separately recruited participant sample. Conditions within an experiment are combined; independent experiments using the same exercise remain separate. The strict analysis retains **126 observations**.

## Find what you need

| File | Contents | Where discussed in the paper |
| --- | --- | --- |
| [Paper_inventory.xlsx](data/Paper_inventory.xlsx) | The 371 papers, search sources, retrieval status, exercise matches, and contributions | Data Collection and Sample; Appendix A |
| [Observation_data.xlsx](data/Observation_data.xlsx) | Outcomes, payoff information, reservation values, controls, and sources before calculating the structural measures | Appendix A |
| [Approval rules](data/approval_rules.csv) | Required agreement rule, its source or unanimity default, and the matching numeric control | Appendix A |
| [Regression data](data/regression_data.csv) | The 141 observations and ten analysis columns | Analytical Strategy |
| [Exercise inventory](data/inventory/exercise_inventory.csv) | The 66 exercises, material sources, and contributions | Appendix A |
| [Starting registry](data/inventory/starting_study_registry.csv) | The fixed 479 review records, linked to 330 papers | Appendix A |
| [Counts and units](data/data_flow.csv) | Search, retrieval, coding, and final observation counts | Appendix A |
| [Data collection and calculations](DATASET.md) | Source priorities, combining conditions, structural measures, and tests | Appendices A–C |
| [Tables](Tables.md) | Main Tables 1–3 and supplementary Tables C1–C4 | Results; Appendix C |
| [Notebook](analysis.ipynb) | Rebuild the data, check the measures, and reproduce every analysis | Appendices A–C |

We read the papers and research materials to code the evidence. The notebook starts from those transcriptions, checks the structural calculations, combines conditions within observations, and creates the regression data. Sources and coding decisions remain attached to the underlying results.

## Run the analysis

Download this folder, extract it, and open a terminal in the extracted folder. With Python 3.12, run:

```bash
python -m pip install -r requirements.txt
python run.py
```

Or open `analysis.ipynb` and choose **Run all** after installing the requirements. Everything is saved in `outputs/`. The code uses relative paths and needs no account or API key. Each resampling check uses 5,000 draws with a fixed seed.

## Main findings

In the main regression model, greater search complexity is associated with lower agreement rates (**b = −.109, p < .001**). Its model with controls explains more variation than the bargaining-zone model with the same controls (**ΔR² = .206; 95% interval [.025, .361]**). Both hypotheses meet their main regression, individual-observation resampling, and single-observation omission criteria.

Appendix A explains data collection and coding. Appendix B explains both structural calculations, which also apply to Studies 2 and 3. Appendix C gives the supplementary procedures and results, including the original main hypothesis analyses reproduced by `original_main_analysis.py`.

The workbook and source files provide numerical transcriptions and citations. Research papers and proprietary teaching documents remain in their respective libraries.
