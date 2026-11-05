# How the data were built

We sought scored negotiations with at least two issues and an observed agreement
or impasse outcome. The fixed registry contains 479 study records from 328 papers
in Warsitzka et al. (2024). Other leads came from the research team, Majer et al.
(2022), Schweinsberg et al. (2022) and Petrowsky et al. (2025). The deduplicated
search list contains 370 papers. Search records are not automatically eligible.

## One main observation is one study

A study means an experiment or independently recruited sample, not a paper or
one reservation-value condition. Independent New Recruit studies, for example,
remain separate rows with their own agreement rates. Reanalyses of one sample
are counted once. Repeated tasks completed by the same sample are combined.

We recovered 169 outcome components linked to 102 existing structural records,
yielding **141 studies from 112 papers** and 66 recorded scenario names. Some
names describe versions of related exercises. The historical Harborco norm
remains in the structural robustness data, but identifies no empirical study.
The excluded Kappes record remains excluded.

## Aggregation within a study

First calculate each identified structure's bargaining-zone share and search
complexity. Then average those measures using the numbers of negotiation
encounters assigned to the corresponding conditions. Use the same weights for
agreement rates. With exact counts, the outcome is total agreements divided by
total negotiations. Agreement derived from impasse is exactly 1 minus impasse.

An overall outcome is not copied into several conditions. If one outcome pools
different known structures, pair it with the corresponding average of separately
calculated structural measures. If condition sizes are unavailable, use equal
weights only across documented possibilities, record this decision, and leave
the negotiation-count weight missing. Do not average payoff tables or reservation
values before calculating the structural measures.

Some existing structural records already summarize a finite set or closed range
of documented possibilities. Their recorded calculations are retained. See
`coding_evidence.csv` and the sources for those earlier calculations.

Examples:

- Dannals et al. (2021), Study 1: combine three RV cells into one outcome,
  1,101/1,276, using the same count weights for structural measures.
- Petrowsky et al. (2025), Study 2b: four seller-threshold conditions yield one
  outcome, 311/1,069, paired with count-weighted structural measures.
- The 31 identified studies using standard New Recruit remain 31 observations.
  Their structural predictors repeat; their agreement rates vary.
- Martin-Raugh et al. (2020): one sample of 42 dyads completed two tasks.
  This is one study observation covering 84 negotiation encounters.

## Source priorities

Outcomes: original counts; original reported rates; matched meta-analytic rates;
identified classroom records; historical teaching norms. The last category needs
an identifiable study to enter the study-level dataset. Exact counts override
rounded rates for the same sample. Counts refer to encounters, not participants.

Structure: administered materials; numerical information in the paper or
supplement; a verified teaching version. Reservation values can be numerical
BATNAs, explicit impasse payoffs or binding acceptance thresholds on the payoff
scale. A minimum attainable agreement score is not a reservation value. Zero
requires evidence. An explicit prohibition on exit imposes no reservation limit.

Main allows documented reconstruction or a finite set / closed range supported
by evidence. Outcomes, reservation values, structural measures, basic controls
and negotiation counts are not statistically imputed.

## Earlier aggregation as a robustness check

`search_complexity_dataset.csv` retains 104 coded records. Its main flag selects
103 observations. Each represents a payoff structure and reservation rule;
independent studies using it are averaged with equal study weights. Counts stay
separate, so this mean need not equal pooled agreements / pooled negotiations.

Its stricter flag selects 75 observations, removing reconstructed structures,
assumed thresholds, outcomes pooled over structures and teaching-note norms
without sample sizes. It can use narrower, directly matched outcome evidence.
This is the unit in the archived plan. The study-level primary unit is a dated
analysis change. The two counts must not be labeled interchangeably.

## Measures and controls

Bargaining-zone share is the proportion of complete offers satisfying the
reservation values and decision rule. Discrete offers are enumerated. Continuous
offers require declared ranges and a sampling distribution.

Search complexity is the proportion of starting offers with no path to the
bargaining zone through one-issue revisions that strictly increase the number
of accepting parties. Every valid path is considered. Equal-acceptance moves
are excluded. Continuous cases need a finite grid defining neighbors. An
unordered sample alone is insufficient. Search complexity cannot exceed one
minus bargaining-zone share, because every acceptable offer is self-reachable.

The five controls are issues, parties, compatible issues, an automated
counterpart and a non-unanimous rule. Fractions describe mixtures of conditions.

## Analysis

Models 1-5 give each study equal weight. Model 6 weights Model 3 by the study's
positive, recoverable negotiation count (140 studies). The same models are
repeated in both structural robustness datasets. Continuous predictors use
the population SD within the model sample; the outcome remains a proportion.

Inference uses HC3 robust errors and two-sided t tests. A singleton dummy is
absorbed for uncertainty on the other slopes. Its coefficient stays, but its
own HC3 SE is unavailable. The code verifies unchanged focal point estimates.
Constant controls are omitted explicitly.

H1, H2 and H4 require the predicted significant coefficient, a 5,000-draw
observation-bootstrap interval in that direction, and significance after each
observation is removed in turn. H3 requires a positive paired difference
R²(M2)-R²(M5), a positive interval and positive differences in every omission.
Supplementary checks allow related errors for shared scenarios, resample or
omit scenario groups, average named scenarios and examine rank correlations.
They do not replace inconclusive primary tests.

## November corrections and replication scope

The 3 November audit held out Kappes et al. (2020) for unsupported reservation
values, removed four reconstructed Café rows from strict, corrected first-session
Hong Kong-U.S. counts and narrowed the strict Graham outcome. Decisions remain
visible in the data.

On 5 November, independent study outcomes were separated, while conditions and
repeated tasks within a study were combined. Stale source labels were corrected.
Nadler et al. (2003) now uses 60/61: one impasse among 61 dyads, retaining two
extreme but valid agreements under the coding rule. Recovered issue-bracketing
denominators restore two negotiation-count weights to the structural robustness
data. No payoff or structural metric changed.

The notebook rebuilds all study rows from `study_outcomes.csv` and the structural
data before analysis. Original papers and the private archive are needed to
audit the preceding extraction. The release does not independently reconstruct
every structural metric from PDFs.
