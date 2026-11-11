# Study 1 data and analysis

## Source retrieval and matching

The fixed starting registry contains 479 records from 328 source documents in [Warsitzka et al. (2024)](https://osf.io/2c9gf/). The paper inventory also records additional search sources. Registry records may refer to conditions within a study. The search list, source recovery, eligibility and the final regression sample are separate counts. The original stopping rule refers to fully matched registry records.

The paper inventory has 370 candidates, of which 347 are marked recovered in the retrieval ledger. Eight papers contributing nine current study observations are still marked unrecovered in that ledger, despite coded outcome and structural evidence in other source records. The flag retains the historical retrieval status. Of the papers marked recovered, 243 have no study in the current analysis and no final screening reason in the released records. These counts describe retrieval and current representation. The inventory does not establish completed eligibility screening for every candidate paper.

We sought an identifiable independent sample that completed a scored negotiation with at least two issues, an observed agreement outcome and enough numerical information to match the outcome to the negotiation structure. The coded files identify the paper or data source, exercise, version, payoff source, reservation rule and outcome. Original agreement counts take priority, followed by original reported rates and matched meta-analytic outcomes. Teaching materials can establish numerical features. An unidentified classroom norm is retained as an exclusion in the inventory. Multiple publications reporting one sample contribute one observation.

## Measures and study construction

For offer x, let A(x) equal one if the offer meets the reservation values and agreement rule and zero otherwise. Bargaining-zone size is the mean of A(x) over the allowed complete offers. Discrete offers are enumerated. For continuous or mixed issues the coded method records the bounds and the sampling or grid rule, which define the offer distribution for the calculation.

For search complexity we count the parties accepting each offer. A reachable offer is in the bargaining zone or has a path to it through one-issue changes that strictly increase that count. Search complexity is the share of offers without such a path. Continuous or mixed calculations use a grid with a defined neighbor rule. The acceptance arrays provide executable inputs for the structures listed in the metric manifest. Other calculations enter as recorded scores with their method and source notes.

`study_outcomes.csv` links coded outcome components to independent studies and structural records. Exact component counts yield the agreement rate by division. Reported rates are retained when only a rate is available. For multiple eligible components in a study, `prepare_data.py` uses negotiation encounter counts as weights when every component has a count. When counts are incomplete, it averages across the documented components and records the assumption. Structural measures and controls use the same allocation as the outcome. Pooled outcomes that already refer to a documented mixture are represented once. The component weights are exported for inspection. A paper may contribute several independent studies, and separate studies using the same exercise retain their own outcomes.

The analysis file contains the study ID, exercise and group, agreement rate, encounter count where recoverable, bargaining-zone size, search complexity, and five controls. The controls are numbers of issues, parties and compatible issues, automated counterpart involvement, and a non-unanimous decision rule. The first three can be condition-weighted counts and the last two can be fractions. Multiple exercises used in the same study form a connected exercise group for inference.

## Models and reporting

Fit three ordinary least squares models to the common complete sample with equal weight per study. Each uses the same basic controls. The first includes bargaining-zone size, the second search complexity, and the third both. The outcome is a proportion. We standardize the two focal predictors and the three numerical counts within the model sample. The two indicators and their fractions retain their original scale.

H1 uses the search-complexity coefficient in the joint model. It must be negative with a two-sided exercise-clustered p value below .05. H2 uses the difference in R² between the search-complexity and bargaining-zone models. Its observed difference and both ends of the paired 5,000-draw exercise-resampling percentile interval must be positive.

The notebook also reports HC3 uncertainty, unadjusted models, rank correlations, study and exercise resampling, and omission checks. The weighted joint model weights by recoverable negotiation counts. The numerical-version comparison averages independent study rates within each linked structural record. The strict comparison uses the coded direct matches and corresponding stricter outcomes. Exercise means and each model's sample and group sizes are available in the generated output.

The 5 November 2026 study-level work preceded the dated amendment. The revised plan concerns the archival study and has two hypotheses. The original specification and its four-hypothesis results remain available in the earlier Git release.
