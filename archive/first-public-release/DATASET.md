# Dataset construction

The dataset was built from published negotiation studies, study supplements, and negotiation teaching materials. The detailed coding rules are in the project's **OSF preregistration materials** folder. This page gives the short version.

## What one row means

One row is one observation: a specific numerical version of a scored, multi-issue negotiation matched to an observed agreement rate. A new payoff schedule, reservation value, set of available choices, number of parties, or agreement rule creates a new observation.

When several eligible samples used the same numerical version, their agreement evidence was combined under the preregistered aggregation rules. Counts were pooled when non-overlapping agreement numerators and negotiation denominators were available. The source and coding method remain recorded in the row.

## How a row entered the dataset

1. The negotiation had at least two scored issues.
2. A reported agreement or impasse outcome could be linked to the version that participants used.
3. The payoff structure, reservation values, available choices, and agreement rule were recoverable well enough to calculate the two structural measures.
4. Agreement rates were taken from the highest-priority available source. A reported impasse rate was converted to agreement rate as `1 - impasse rate`.
5. No agreement rate, payoff structure, reservation value, structural measure, basic control, or negotiation count was statistically imputed.

`main_eligible` marks the main analysis. `strict_eligible` marks the stricter analysis, which removes observations that rely on structural assumptions, payoff reconstruction, pooling across different numerical versions, or historical teaching-material agreement rates without a sample size.

## Main variables

| Columns | Meaning |
| --- | --- |
| `observation_id`, `negotiation_scenario`, `scenario_version` | Stable row identifier and plain-language scenario labels. |
| `agreement_rate`, `agreements`, `negotiations` | Observed agreement proportion and its numerator and denominator when recoverable. |
| `bargaining_zone_share` | Proportion of possible deals acceptable to every party. |
| `search_complexity` | Proportion of starting deals with no jointly improving one-issue path to the bargaining zone. |
| `number_of_issues`, `number_of_parties`, `number_of_compatible_issues` | Basic structural controls. |
| `automated_counterpart`, `non_unanimous_rule` | Indicators for an automated or AI counterpart and a non-unanimous agreement rule. |
| `main_eligible`, `strict_eligible` | Analysis eligibility flags. |
| `strict_agreement_rate`, `strict_agreements`, `strict_negotiations` | More narrowly matched outcome evidence used in the strict analysis when it differs from the main row. |
| `reservation_values_or_rule` | Short record of the acceptance thresholds or rule used in coding. |
| `payoff_source`, `agreement_rate_source`, `strict_agreement_rate_source`, `source_link` | Provenance for the structural and outcome data. |
| `agreement_rate_coding`, `coding_note` | How the agreement rate was obtained and any material coding decision. |

The repository does not include raw payoff schedules from proprietary teaching scenarios. Their calculated measures and source citations are retained in the public dataset.
