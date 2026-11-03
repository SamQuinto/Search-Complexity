# How the dataset was built

We searched for completed, scored negotiations with at least two issues and an
observed agreement or impasse outcome. The fixed starting registry contains
479 study records from 328 papers in Warsitzka et al. (2024). Additional leads
came from the research team, Majer et al. (2022), Schweinsberg et al. (2022), and
Petrowsky et al. (2025). The plan listed 371 papers; a later duplicate check
reduced the paper inventory to 370. A search record is not automatically an
eligible regression observation.

## One observation

An observation connects an observed agreement rate to a particular payoff
schedule, choice set, reservation values and agreement rule. Changes in those
features can create separate observations under the same scenario name.

Within-study conditions using the same structure are combined by pooling
agreement and negotiation counts. Independent studies using the same structure
contribute the **unweighted mean of their study rates**. Their pooled counts
are retained separately, so the primary rate need not equal agreements / negotiations.

If an outcome pools different known structures, we first calculate both
structural measures separately. We average them using version-specific group
counts when known and equal weights otherwise. These pooled rows enter main
but leave strict. A pooled rate is never copied into several unidentified versions.

## Source priorities

For outcomes: original counts; original reported rates; matched meta-analytic
rates; identified classroom records; historical teaching-note rates.
Agreement derived from impasse is exactly 1 minus impasse.

For structure: materials actually administered; the paper or supplement; a
verified teaching-case version. Reservation values may be assigned numerical
BATNAs, explicit impasse payoffs or binding acceptance thresholds on the payoff
scale. A minimum obtainable agreement score does not establish a reservation value.
Zero requires evidence. An explicit prohibition on exit imposes no reservation limit.

Main permits documented structural reconstructions or values supported by a
finite set or closed range. Strict removes reconstructed structures, assumed
thresholds, outcomes pooled across different structures, and teaching-note
norms without sample sizes. The full rules are in the archived OSF plan.

## Measures and fields

Bargaining-zone share is the share of complete offers satisfying the reservation
values and decision rule. Discrete offers are enumerated; continuous offers
require stated ranges and a sampling distribution.

Search complexity is the share of starting offers with no path to the bargaining
zone through one-issue changes that strictly increase the number of accepting
parties. Every possible valid path is considered. Continuous cases require an
explicit grid defining neighbors. An unordered sample alone cannot define it.

| Fields | Meaning |
| --- | --- |
| observation_id, negotiation_scenario, scenario_version | Unique row, named scenario and version description. |
| agreement_rate, agreements, negotiations | Primary study-mean rate and pooled counts when recoverable. Negotiations counts encounters, not participants. |
| bargaining_zone_share, search_complexity | Structural measures on 0-1 scales. |
| number_of_issues, number_of_parties, number_of_compatible_issues | Structural controls. |
| automated_counterpart, non_unanimous_rule | Indicators; a fractional value describes the composition of a pooled row. |
| main_eligible, strict_eligible | Analysis flags. |
| strict_agreement_rate, strict_agreements, strict_negotiations | Outcome evidence for the narrower strict match. |
| reservation_values_or_rule, payoff_source | Threshold and structural provenance. |
| agreement_rate_source, strict_agreement_rate_source, source_link | Outcome provenance. |
| agreement_rate_coding, coding_note | Calculations and decisions. |

The CSV contains previously calculated structural measures. Nine included
records with complete machine-readable schedules and explicit reservation values
were independently recalculated in this audit and matched to floating-point
precision. The other structures retain their stored calculations and recorded methods.

## Analysis

Models 1-5 give each observation equal weight. Model 6 weights the Model 3
specification by a positive, recoverable negotiation count covering the outcome
evidence in that row. It retains the primary study-mean outcome.

Continuous predictors are standardized within each model's included rows using
the population SD (ddof=0); the outcome stays a proportion. Binary controls and
fractional compositions retain their coding. No outcomes, structural measures,
basic controls or negotiation counts are statistically imputed.

Inference uses HC3 robust errors and two-sided t tests. In strict, automated
counterpart has no variation and is not estimable. The non-unanimous-rule dummy
occurs once: its coefficient is retained but its HC3 uncertainty is unavailable.
The remaining coefficients and covariance are calculated after absorbing that
singleton dummy, which preserves their point estimates and residual degrees of
freedom. This avoids silently dividing by zero in HC3.

For H1, H2 and H4, support requires the predicted significant coefficient,
a 5,000-draw observation-bootstrap interval in that direction, and a predicted
significant coefficient in every leave-one-observation-out refit. For H3, the
paired R-squared difference must be positive, its bootstrap interval must exclude
zero, and every omission comparison must remain positive. Supplementary checks
are reported separately.

## Corrections in the 3 November 2026 audit

The previous file had 104 main and 80 strict observations. All records remain,
but main now uses 103 and strict uses 75:

- Kappes et al. (2020) is held out because zero was inferred from the bottom of
  the agreement scale without sufficient reservation-value evidence.
- Four Sale of a Café rows remain in main but leave strict because their seller
  schedule was reconstructed.
- The four Arunachalam, Wall, and Chan (1998) outcomes are corrected to the
  printed first session: 70/70, 64/64, 34/35 and 32/32. Denominators total 201
  groups. The older numbers counted both sessions.
- Strict Graham now uses the directly matched 1985 outcome, 48/49.
- Stale Sweet Shops threshold text and a misattributed Falcao coding label are
  corrected without changing their structural scores or main outcomes.

The original release and full correction log are retained privately.
