# Acceptance-rule checks

The main calculation counts a numeric payoff as acceptable when it is **above the reservation value**. These checks ask whether the findings change when equality also counts, or when two documented assumptions vary.

- [comparison.csv](comparison.csv): the main and strict results, including the 5,000-draw intervals and required single-observation checks.
- [point_scenarios.csv](point_scenarios.csv): point estimates across all 123 combinations of the two assumptions. These are not 123 resampling analyses.
- [structural_metrics.csv](structural_metrics.csv): the search-complexity and bargaining-zone values for the full comparison cases.
- [secondary_significance_changes.csv](secondary_significance_changes.csv): coefficients whose p value crosses .05 in a comparison case.
- [provenance.json](provenance.json): calculation settings, source-file checks and the number of observations.

`primary_gt` uses the main rule; `inclusive_ge` also accepts equality. The six other full cases vary the allocation of negotiations across Beersma and De Dreu’s (2002) four conditions and the possible bargaining-zone share for Northcraft et al.’s (1998) incomplete tables. The data documentation explains these assumptions. The strict dataset excludes both affected observations, so these six changes leave its results unchanged.

Run the main script or notebook to reproduce these files and Table C5. Detailed outputs for each case are also saved locally in this folder; they are not duplicated in GitHub.
