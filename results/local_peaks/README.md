# Study 2 local peak check

We counted offers outside the bargaining zone that had no one-issue revision that would increase the number of parties willing to accept. A revision could change the selected issue to any of its alternatives. We used the same payoff information, reservation values, and approval rules as in the main analysis. For continuous and mixed negotiations, we counted peaks on the grids used for search. For *The Player*, we estimated the count from the same 65,536 sampled starting offers per reservation assignment while checking all possible one-issue revisions. When an observation combined conditions, we applied the same weights to the peak counts as to the structural measures for that sample.

The count could be calculated or estimated for all 140 main observations and all 124 observations in the stricter sample. We repeated the five regressions with the count in place of search complexity, along with the 5,000 paired resampling draws and the checks omitting one observation at a time.

| Sample | Local peak coefficient | *p* | Model fit difference, peak count minus bargaining-zone size | 95% resampling interval for fit difference |
| --- | ---: | ---: | ---: | ---: |
| Main | .001 | .9997 | −.028 | [−.135, .055] |
| Stricter | −.013 | .603 | −.048 | [−.223, .085] |

The count did not recover either archival hypothesis. With the original measure, both hypotheses held on the same samples. A count depends on the total number of possible offers and, for continuous issues, how finely we divide the range. For example, *The Player* has about 47.8 million possible offers and an estimated 29.7 million peaks. The original measure describes the share of starting offers that cannot reach agreement through improving revisions, including offers that lead to a peak later.

Run `python scripts/local_peaks.py` from the repository root to regenerate these results. [Hypothesis checks](hypothesis_checks.csv) · [Counts by payoff structure](payoff_counts.csv) · [Counts by main observation](main_observation_counts.csv) · [Counts by stricter observation](strict_observation_counts.csv)
