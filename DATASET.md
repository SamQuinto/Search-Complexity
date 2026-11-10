# How we built the Study 1 dataset

This page follows the evidence from the search list to the final dataset.
It summarizes the coding; individual sources and decisions remain in the data.

## 1. Identify and recover papers

We selected 479 study records linked to 328 source documents from the
[Warsitzka et al. (2024) replication materials](https://osf.io/2c9gf/).
Other leads came from the research team and related research, including
Majer et al. (2022), Schweinsberg et al. (2022) and Petrowsky et al. (2025).
The [paper inventory](data/search/paper_inventory.csv) records each paper's
identified sources. It contains 370 deduplicated papers, with 347 marked recovered.
Being on the search list does not establish eligibility.

The [starting registry](data/search/starting_study_registry.csv) preserves the
479 records and their paper links. Some registry records are conditions rather
than independent studies. Its older column labels retain the earlier screening
list's size; the current inventory contains 370 rows. Do not interpret 141/479
as a verified study recovery percentage.

## 2. Read and code the sources

We examined papers, supplements, replication data and teaching materials from
providers including DRRC, NTR and PON. We sought scored negotiations with at least
two issues, an observed agreement outcome, and recoverable choices, payoffs and
acceptance rules. Single-issue or non-scored tasks, hypothetical offer evaluations,
duplicate samples and unsupported numerical structures are not eligible.

For agreement outcomes, priority is original agreement/negotiation counts,
original reported rates, then matched meta-analytic records. Identifiable classroom
samples can contribute evidence; a historical teaching norm without an identifiable
study does not enter the study-level analysis. Agreement rate is agreements divided
by negotiation encounters. It is exactly one minus the impasse rate when those
are complementary outcomes for the same sample. Participants are not negotiation
encounters, and exclusions are not automatically impasses.

For structure, use administered numerical materials, numerical information in
the paper or supplement, then a verified teaching version. Record reported changes
to the original exercise. A scenario name alone does not prove an exact match.

Reservation values can be established by explicit acceptance thresholds, numerical
alternatives to agreement, or stated impasse payoffs on the same payoff scale.
A minimum attainable agreement score is not a reservation value. Zero requires
supporting evidence. An explicit prohibition on exit imposes no reservation limit.
Use the recorded decision rule for multiparty agreement.

The main data allow documented reconstruction and finite sets or closed ranges of
possibilities supported by evidence. They do not permit arbitrary invented payoffs
or reservation values. The stricter structural subset removes the recorded
reconstructions, assumed thresholds and specified pooled or uncertain matches.
Outcomes, structural measures, basic controls and negotiation-count weights are
not statistically imputed in this release.

See [coding_evidence.csv](data/sources/coding_evidence.csv) for calculation methods,
sources and decisions, and [structures.csv](data/sources/structures.csv) for
structural scores and eligibility flags. Source extraction requires the original
materials; this repository does not independently recreate every score from PDFs.

## 3. Calculate structural measures and match outcomes

**Bargaining-zone share** is the fraction of allowed complete offers acceptable
under the reservation values and decision rule. Discrete choices are enumerated.
Continuous or mixed choices require declared bounds and a sampling distribution.

**Search complexity** is the fraction of starting offers from which no path reaches
the bargaining zone through one-issue revisions that strictly increase the number
of accepting parties. Every valid path is considered, rather than one greedy path.
Equal-acceptance moves are excluded. Continuous issues also need defined neighbors,
usually a finite grid; an unordered random sample alone does not define paths.
Each record's exact or sampled method must be retained.

One structural record specifies the numerical payoffs and acceptance rule; some
records summarize documented possibilities. They are not all unique named
exercises or perfectly verified study editions. The structural file retains
104 records: 103 eligible for its main aggregation, including 75 in its stricter
subset. Held-out records remain visible for audit.

The [outcome crosswalk](data/sources/study_outcomes.csv) contains 169 components
linked to 102 structural records. Each component identifies the study, outcome
source and matched structure. A pooled rate is not copied into several studies
as though each had separately reported it. Recoverable independent study outcomes
remain separate; an inseparable cross-study aggregate needs an explicit inclusion
decision rather than invented study-specific rates.

## 4. Build one observation per independent study

An experiment or independently recruited sample contributes one main observation.
Independent studies using the same scenario retain their own agreement rates.
Conditions and repeated tasks completed by the same sample are combined.

Calculate structural measures separately before aggregation. Then average them
within a study using condition negotiation counts and the same allocation as the
outcome. With exact counts, agreement is total agreements / total negotiations.
Never calculate metrics from an averaged payoff table or reservation value.
When condition allocations are unavailable, documented equal weighting is used;
an unavailable count is not invented for weighted regression. Earlier structural
records can also contain recorded averages over supported possibilities.

For example, Dannals et al. (2021), Study 1 combines three reservation-value
conditions into 1,101/1,276 agreements. Petrowsky et al. (2025), Study 2b combines
four conditions into 311/1,069. The 31 standard New Recruit studies remain separate.
Martin-Raugh et al. (2020) contributes one study with 84 encounters because the
same 42 dyads completed two tasks.

The notebook joins the crosswalk to structural scores, rebuilds all 141 rows and
checks them against [study_level_dataset.csv](data/study_level_dataset.csv).
The resulting studies link 112 recorded paper citations and 66 scenario-name
strings. Name groupings used for supplementary analyses are documented in code.

## 5. Analyse the final dataset

The basic controls are issues, parties, compatible issues, an automated counterpart
and a non-unanimous decision rule. Fractions can represent mixtures of conditions.

| Model | Predictors |
| --- | --- |
| M1 | Search complexity |
| M2 | Search complexity + basic controls |
| M3 | Search complexity + bargaining-zone share + basic controls |
| M4 | Bargaining-zone share |
| M5 | Bargaining-zone share + basic controls |
| M6 | M3 weighted by negotiation encounters with recoverable positive counts |

M1–M5 give each study equal weight. M6 includes 140 studies. Continuous predictors
are standardized within the model sample; agreement remains a proportion.
The notebook reports coefficients, uncertainty, model fit, 5,000-draw resampling,
omission checks and the supplementary analyses, including inconclusive results.
It explains the HC3 errors and singleton-control handling in the code.

The earlier structural aggregation averages independent study rates within each
payoff/reservation combination. Its 103-row main and 75-row strict analyses are
robustness checks, not additional study observations. They use the included
eligibility flags and strict outcome columns.

The [saved results](results.json) copy the existing 5 November tables without
rounding or rerunning them. Each key names the corresponding CSV written to
`outputs/` by the notebook. `study_correlations.csv` and
`study_descriptive_statistics.csv` support the descriptive table; `coefficients.csv`
and `model_fit.csv` support the regression table; `hypothesis_tests.csv`,
`bootstrap_intervals.csv` and `omission_checks.csv` report the main checks.

## Preregistration and scope

The detailed original coding plan is in the project's OSF preregistration
materials. Its permanent public registration URL still needs to be recorded here.
The primary study-level unit is an analytical revision dated 5 November 2026;
the archived plan used the earlier structural aggregation. The fixed registry
and recovered-study crosswalk do not yet establish the stopping-rule denominator.

The notebook reproduces aggregation and statistics from coded inputs. It was
previously run in a relocated folder with zero cell errors and matching saved
statistical tables. Reorganizing this release changes file locations and
documentation, not numerical data or statistical code. Full independent
re-extraction from the licensed source library remains a separate audit task.
