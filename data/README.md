# Data and coding

Preregistration: https://osf.io/wtgxc

The paper's Appendix A explains data collection and coding; Appendix B explains the structural calculations; Appendix C explains the supplementary analyses. Paths below are relative to the repository's main folder. The main script and notebook rebuild `data/regression_data.csv` from the coded payoffs and outcomes, check its payoff column, and prepare the stricter and combined-payoff comparisons. Use `--use-released-data` to load the released main dataset directly while keeping its payoff-column checks. Follow the [main README](../README.md) for either route. The code is in [scripts](../scripts/) and the tables are in [results/tables](../results/tables/).

## From the search to the observations

The search starts with the replication data shared by Warsitzka et al. (2024), [OSF 2c9gf](https://osf.io/2c9gf/), and adds papers identified through Majer et al. (2022), Petrowsky et al. (2025), and the research team's search. Schweinsberg et al. (2022) was also consulted; the available discovery records do not separately attribute additional papers to that review.

The fixed starting list has 479 review records linked to 330 papers. A review record need not be an independent experiment: some papers contribute several experiments or condition results. The combined inventory has 371 distinct papers. Local file checks verify 345 complete articles or relevant complete chapters. Eight contributing papers have usable research evidence without a verified local full article. Therefore, 110 contributing papers are not simply a subset of the 345 locally verified full texts. `data/data_flow.csv` reproduces the counts and identifies their units.

The retained evidence contains 166 agreement-result records. Combining the results within each experiment gives 140 observations. These use 100 payoff records across 63 named negotiation exercises. A payoff record identifies a table or function with its reservation values and agreement rule. Some records contain a documented combination of conditions when their agreement outcomes cannot be separated. They are not additional observations in the main regression.

`data/inventory/registry_observation_links.csv` connects 140 original review records to 125 current observations. Another 15 observations come from outside those starting records. These are final-data links, not a dated record of how many matches existed on the search stopping date.

The [paper workbook](Paper_inventory.xlsx) is the readable inventory. Its machine-readable counterpart is `data/inventory/paper_inventory.csv`. `observation_papers.csv` links each observation to its paper. Discovery-source tags can overlap; they identify how a paper entered the search, not necessarily where its agreement rate was obtained.

## What can enter

An observation must come from a completed, scored negotiation with at least two issues. It needs an agreement outcome for an identifiable experiment or participant sample and enough payoff, reservation-value, option, party, and approval-rule information to calculate the measures and controls under the rules below. Automated counterparts can be included when the outcome comes from actual research participants.

Single-issue or unscored exercises, hypothetical-offer evaluations, duplicated samples, simulated agreement rates, and general classroom agreement norms do not enter. Separate publications of the same participants count once. Valid agreement rates of zero and one remain in the data. Results do not determine inclusion.

## Where each value comes from

For agreement outcomes, we first use the numbers of agreements and negotiations in the article, supplement, or shared research data. The two numbers must describe the same attempts. If counts are unavailable, we use the stated agreement percentage. An impasse percentage becomes an agreement percentage by subtracting it from 100. If these materials provide no usable outcome, we use a result clearly matched to the experiment in a review's data. `data/agreement_sources.csv` and the observation workbook identify those sources. Kray et al. (2004), Study 2, for example, contributes 32 agreements in 34 negotiations from Warsitzka et al. (2024), workbook sheet `Tabelle1`, Excel row 214 (W0213).

For payoffs and acceptance rules, materials administered to participants take priority, followed by numerical information in the article or supplement, then the identified teaching exercise. We apply changes described by the researchers and document disagreements between sources. Provider and study links are in the exercise inventory. `data/coding_sources.csv` records the sources selected for each result.

A reservation value is a stated minimum for acceptance or the payoff a party can secure without a deal. A numerical BATNA, outside-option payoff, or impasse payoff can supply it when it is on the negotiation's payoff scale. Zero requires an explicit source or a scale defined as gains above the outside option. A qualitative BATNA does not establish a numerical threshold. An opening offer is not a reservation value unless the study identifies it as one.

The primary calculation counts a party as accepting only when its payoff is **strictly greater than its reservation value (> RV)**. The inclusive >= RV calculation is a sensitivity check. Source instructions retain their actual inequalities; the operative calculation rule is recorded separately. For Liu et al. (2019), both binding boundaries are 900: the source rejects totals of 900 or less. The stable payoff ID ending `r925_r925` is a historical identifier, not the operative reservation boundary. The linked numerical schedule permits totals between 900 and 925; >900 accepts them.

For approval, use the rule in the study or matching exercise materials. If no alternative rule is stated, assume that all parties must agree. This convention applies to the main and strict data; reservation values still require numerical support. `data/approval_rules.csv` distinguishes the default from rules identified in the materials and reconstructed programmed acceptance. The workbook gives these descriptions beside every observation, condition, and payoff record. The control is zero for unanimity, one for non-unanimity, or the negotiation-count weighted share when an experiment uses both rules. The data builder checks that the descriptions agree with the numeric control.

## Combining conditions

We calculate the structural measures for each payoff table and reservation-value combination before combining conditions. With counts, we sum agreements and divide by total negotiations. Structural measures and controls use the same negotiation-count weights. For example, 24/30 and 56/70 agreements become 80/100, with structural weights of .30 and .70.

If only a combined agreement rate is available within an experiment, it is used once and matched to the conditions it covers. Missing condition sizes lead to equal structural weights, with an assumption note, unless every predictor is identical across conditions. Several experiments using the same exercise retain separate outcomes. An inseparable agreement outcome across independent experiments does not enter the main observations. Repeated tasks performed by one sample stay together in one observation; their attempt count is recorded.

`data/within_payoff_weights.csv` records combinations inside a payoff record. `data/derived/component_evidence.csv` records how source results are combined within each observation. For Arunachalam et al. (1998), the 13 remaining reservation-value cells have an exact combined outcome of 270/276 agreements; their allocation across cells is unknown. The main observation uses 291/338 agreements for the full experiment. Its strict counterpart retains the separately recoverable three cells and their 21/62 outcome.

Beersma and De Dreu (2002) report 47 symmetrical/44 asymmetrical groups and 46 unanimity/45 majority groups, but not their joint allocation. All eight motive-by-rule-by-symmetry cells are populated. The main calculation averages the 41 feasible integer allocations, giving weights [24, 23, 22, 22]/91 for symmetrical-unanimity, symmetrical-majority, asymmetrical-unanimity and asymmetrical-majority. These are assumption-based weights, not observed cell counts. Because allocation affects >RV measures, this record is excluded from the strict-evidence sample.

Gunia et al. (2013), Study 4, contributes one 40/42 outcome and one pooled New Recruit record. The 42 protocol-compliant attempts exclude three wrong-first-offerer dyads and retain two impasses. The recruiter/candidate reservation orders [4500, 0] and [0, 4500] have identical values for all five structural measures and counts under >RV, so their unknown allocation does not prevent strict inclusion. This is an independent sample from the paper's Moms.com Study 2.

## Structural calculations

Bargaining-zone size is the share of complete offers satisfying the >RV acceptance test and approval rule. With fixed choices, the code lists the possible combinations, calculates each party's payoff, and counts acceptable offers. For a term such as price that can take any value within a range, the code calculates the acceptable share over the exercise's specified range. Payoff functions allow exact calculation in some cases; recorded grids or reproducible samples are used in others. The paper's Appendix B explains continuous and mixed issues and how the ranges and weights define the share.

Search complexity is the share of starting offers that cannot reach agreement through revisions that change one issue and strictly increase the number of parties whose payoffs exceed their reservation values. Offers differing on one issue have Hamming distance one (Hamming, 1950); the size of the change on that issue can be large or small. The calculation checks whether any improving path exists, and an offer already in the bargaining zone is reachable. This adapts the local-search intuition of Kauffman and Levin (1987) and Levinthal (1997) to acceptance in negotiations.

All 100 active structural calculations can be rebuilt from the supplied inputs and declared assumptions. Ninety-seven payoff records contain numerical tables or functions. Three Northcraft et al. (1998) versions use partial source tables and a conditional endpoint proof rather than complete numerical schedules. Unprinted point values are not invented. `data/derived/payoff_metric_checks.csv` identifies the calculation used for each record.

Martin-Raugh et al. (2020)'s Fundraiser and Robot tasks remain in the source outcome ledger and inventories but are excluded from both analysis samples pending complete payoff tables for both roles. Matching final selections establish a formally complete proposal; they do not establish that every proposal meets the parties' reservation values. The zero timeout award and possible negative points invalidate an all-complete-offers bargaining-zone proof. [Excluded payoff records](inventory/excluded_payoff_records.json) hold their source evidence and exclusion reasons.

Calhoun and Smith (1999)'s pooled result and O'Connor et al. (2005)'s Honors Class task are excluded because no-limit instructions do not establish a numerical outside payoff or compulsory settlement. The Calhoun high-minimum conditions cannot be separated from the pooled outcome. O'Connor Study 1 retains its separately reported Confetti Time 1 result (.282, 131 dyads), with the complete schedule and 780-point boundaries. Excluded outcomes remain in the source ledger.

`data/raw_payoff_catalog.json` holds the payoff data, functions, rules, sources and assumptions. The Python modules supply the declared numerical procedures. For The Player in Kray et al. (2004), the main calculation averages the 6,000/3,000 and 3,000/6,000 role assignments with equal weights because their separate sample sizes are unavailable. The historical study's exact table match remains uncertain. For Sale of a Café, both payoff functions are verified from the study data, but the automated buyer-score acceptance cap is a reconstruction; its program logic is unavailable. Both ambiguities remain visible and do not enter the strict data.

## The payoff JSON column

The main [regression dataset](regression_data.csv) has `payoff_json` immediately after `observation_id`. The main script and notebook select the numeric analysis columns by name. Both data-preparation routes rebuild the JSON column from the supplied source records and stop if payoff/source controls disagree with the coded inputs.

Each cell is a JSON object with `schema_version`, `coverage`, `calculation_rule`, `weighting`, `components` and `payoffs`. The calculation rule states the operative numeric RV comparison. `components` links the observation to its payoff records and gives its negotiation counts and weights. Each payoff record contains the source catalogue entry, approval-rule evidence and any documented internal allocation. These are two distinct levels of weights: source-result components within the observation, and numerical versions within a payoff record.

For discrete tables, `catalog.schedules` holds issue names, option labels and nested `payoffs` arrays. A payoff row gives the parties' values in the listed order. `catalog.components[].schedule_ref` resolves inside this same object; repeated tables are stored once. Each component also gives reservation values, required approvals, mandatory parties and its aggregation weight. A missing numerical threshold remains `null`; a programmed acceptance rule is recorded separately where applicable.

Continuous and mixed cases retain their numerical formulas, domains, parameter values, grids, sampling settings and version weights in `payoff_function_input` and `calculation_settings`. Salary and a payment-share simplex retain their logical issue grouping. The helper uses the existing exercise-specific calculators; it checks the registered formula specification and rejects unsupported edits rather than evaluating formula text. Numerical estimates retain the released procedures and fixed sampling settings.

From the repository folder, with the normal requirements installed:

```bash
python scripts/supporting/payoff_info.py --observation SRU0286
python scripts/supporting/payoff_info.py --check
```

To use a copied cell, save its JSON text as `cell.json` and run `python scripts/supporting/payoff_info.py --cell cell.json`. In Python, `from scripts.supporting.payoff_info import calculate` exposes `calculate(cell_text)`. Calculation needs the cell and the supporting calculator code; it reads no separate data file or stored structural score.

Coverage is 97 numerical payoff records and three conditional Northcraft proof records across 140 observations. Complete numerical schedules remain unavailable for `NORTHCRAFT1998_STUDY1`. A printed compatible issue establishes search complexity 0 under >RV. Bargaining-zone share .999872 additionally assumes one zero-total package per role, with the two packages distinct; the unprinted endpoint values are not numerically recovered. This assumption excludes the three records from strict inclusion. The paper directly reports six issues, two parties and one compatible issue. These counts and their exact pages appear in `source_verified_controls` and `controls_source`; the helper identifies them as directly reported controls and checks them against the coded inputs. [payoff_input_issues.csv](payoff_input_issues.csv) lists these three numerical-coverage gaps within one observation.

Northcraft entries include twelve printed templates across the three conditions in `partial_source_tables`. The two unprinted integrative schedules per condition remain `null`; the stated nonlinear maximum 259 and the unresolved physical-issue mapping remain explicit. Those partial arrays are evidence, rather than a complete six-issue schedule.

The Kern Player and Murnighan development schedules pair each role's values by the same named physical alternative, even where the printed role tables order options differently. Their compatible counts are one and two, respectively. Aaldering and De Dreu's five printed issues have opposed preferences and zero compatible issues. Input preparation and `--check` fail on any remaining control mismatch. Compatible counts for Cartoon/Moms.com treat optional Juniors inclusion as the documented common-benefit direction; the price within inclusion remains opposed.

Other existing source assumptions remain attached to their models: the Café cap is a reconstructed programmed rule with a `null` seller reservation value, the Kray Player role-table match is uncertain, the Kong reservation pairings use the documented equal grid, and the Moms.com contingent-option support is reconstructed. The helper does not fill those gaps.

## Models and checks

The five controls are issue count, party count, compatible-issue count, automated/AI counterpart, and agreement without unanimity. Compatible issues are those on which parties prefer the same choice or direction. Controls can be weighted averages across conditions. No missing agreement rate, payoff, reservation value, structural measure, basic control, or negotiation count is statistically imputed.

All five main models use the same complete observations and HC3 robust standard errors, allowing unexplained variation in agreement rates to differ across observations (Long & Ervin, 2000; MacKinnon & White, 1985). Models 1 and 2 contain search complexity without and with controls. Model 3 contains both structural predictors and the controls. Models 4 and 5 contain bargaining-zone size without and with controls. Continuous predictors and the three counts are standardized; agreement rate stays on 0–1.

The final number and mix of observations depend on which research evidence can be recovered. The stopping rule is a practical search rule rather than a power calculation fixing the final sample size. We therefore require a main result and two stability checks before supporting either hypothesis.

H1 requires a negative search-complexity coefficient in Model 3 with a two-sided p value below .05, a 95% observation-resampling interval entirely below zero, and a negative coefficient with p < .05 after every single-observation omission. H2 compares Model 2 with Model 5 on the same observations and controls. Its R² difference must be positive, its 95% resampling interval must be entirely above zero, and the difference must remain positive after every single-observation omission. The output reports each condition and their combined result separately.

Each resampling draw selects whole observations with replacement, retaining the dataset's size. Both comparison models use the same draw. The percentile interval uses 5,000 draws (Efron & Tibshirani, 1993); the large number reduces variation caused by the resampling procedure itself. Removing one observation at a time checks whether any individual result is essential, following the logic of case-deletion diagnostics (Cook, 1977). The paper's Appendix C explains these procedures and how to read their results.

Supplementary checks start with 124 strict observations from 144 eligible source-result components. Source-supported arithmetic, a sampled structural measure, or an unknown condition allocation that cannot change any predictor can qualify. Unresolved numerical matches, reconstruction assumptions and unknown allocations that affect a predictor cannot. Arunachalam's strict observation uses its three recoverable cells. `data/derived/observation_eligibility.csv` records every decision.

The main and strict observations receive resampling and single-observation omission checks for Model 3 and the Model 2 versus Model 5 comparison. Model 6 repeats Model 3 with negotiation-count weights, retains 139/123 observations, and receives the corresponding resampling and omission checks. Weights count negotiation attempts, not individual participants.

The combined-payoff comparison averages independent experiment rates within each identical payoff record, including any documented combination retained within that record. It contains 100 records, or 81 under strict inclusion, and receives the five HC3 regressions. Its purpose is to examine the influence of repeated use of the same payoff information. Main tests treat independently recruited participant samples as independent observations.

## References

Cook, R. D. (1977). Detection of influential observation in linear regression. *Technometrics, 19*(1), 15–18. https://doi.org/10.1080/00401706.1977.10489493

Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*. Chapman & Hall. https://doi.org/10.1201/9780429246593

Hamming, R. W. (1950). Error detecting and error correcting codes. *The Bell System Technical Journal, 29*(2), 147–160. https://doi.org/10.1002/j.1538-7305.1950.tb00463.x

Kauffman, S., & Levin, S. (1987). Towards a general theory of adaptive walks on rugged landscapes. *Journal of Theoretical Biology, 128*(1), 11–45. https://doi.org/10.1016/S0022-5193(87)80029-2

Levinthal, D. A. (1997). Adaptation on rugged landscapes. *Management Science, 43*(7), 934–950. https://doi.org/10.1287/mnsc.43.7.934

Long, J. S., & Ervin, L. H. (2000). Using heteroscedasticity consistent standard errors in the linear regression model. *The American Statistician, 54*(3), 217–224. https://doi.org/10.1080/00031305.2000.10474549

MacKinnon, J. G., & White, H. (1985). Some heteroskedasticity-consistent covariance matrix estimators with improved finite sample properties. *Journal of Econometrics, 29*(3), 305–325. https://doi.org/10.1016/0304-4076(85)90158-7

Full citations for the reviewed papers and every contributing observation are in the two workbooks.
