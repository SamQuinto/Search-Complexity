# Study 1 · Agent-based model

The model examines whether incremental search makes it harder to reach agreement as search complexity rises, and whether allowing agents to change more issues at once improves agreement. These comparisons motivate the predictions tested in the empirical studies.

From the repository root, install the [requirements](../requirements.txt) and run:

```bash
python study1_agent_based_model/figures.py
python study1_agent_based_model/replay.py
python study1_agent_based_model/local_peaks.py
```

The first command draws the figures from the saved results. The second replays the three search conditions for the first six-party negotiation and checks the results against the saved values. Use `--parties 2` to replay the dyadic conditions and `--scenarios 1000` to replay all 302,700 simulations for the chosen group size. The third command counts local peaks and checks whether the results hold when complexity is measured that way.

| File | Contents |
| --- | --- |
| [Figure 1](results/figure_1_search_example.png) | Four schematic offer grids crossing low and high search complexity with small and wide bargaining zones |
| [Figure 2](results/figure_2_simulated_agreement.png) | Six-party agreement rates under the three search rules, by search-complexity range |
| [Appendix figure](results/appendix_figure_two_party.png) | The same comparison for two-party negotiations |
| [Figure estimates](results/figure_2_estimates.csv) | Agreement rates and the number of negotiation structures in each range, for both group sizes |
| Simulation conditions. [Six parties](data/simulation_conditions.csv) · [Two parties](data/simulation_conditions_two_party.csv) | Agreement rate, run count, and structural measures for each negotiation under each search rule |
| Negotiation inputs. [Six parties](data/negotiations.json.gz) · [Two parties](data/negotiations_two_party.json.gz) | The generated payoff tables and reservation values |
| [Model code](supporting/negotiation_search_engine.py) | The engine used to produce the saved simulations |

## How the comparison works

The two group sizes use the same 1,000 generated base structures, each with ten issues, a nonempty bargaining zone, and results for all three search rules. Agents could change one issue, up to two issues, or up to three issues in each counteroffer. The rule for choosing a reference offer, the opening rule, and the stopping rule were the same throughout. On each counteroffer, the agent had a 50% chance of drawing its reference from the group's offer history and otherwise used its own history. Among untried offers within the permitted distance, the agent chose the offer with the highest payoff to itself. The run ended in agreement when it found an offer that met all parties' reservation values.

The saved model treats a payoff equal to the reservation value as acceptable. That same comparison is used to calculate search complexity and bargaining-zone share. Search complexity is the share of offers from which there is no sequence of one-issue changes that continually increases the number of parties whose reservation values are met and ends in agreement. Figure 1 illustrates the difference between the size of a bargaining zone and its accessibility along a particular search path. Each grid has 100 offers, with one issue on each axis. The gray areas contain 10 or 20 mutually acceptable offers. Both paths converge on the same cell in all four panels. In the high-complexity panels, the cell is outside the bargaining zone and changing both issues would reach the shaded area.

Both agreement-rate figures use five ranges of width 20 percentage points. The first includes both endpoints and subsequent ranges include only their upper endpoint. Each negotiation gets equal weight. There are 100 simulations per negotiation and search rule, with 1,000 per rule for one negotiation in each group size. The same seed sequence is used for a given negotiation across the three rules. The six-party inputs are the same as the archived search-complexity comparison in Figure B2 of the computational model replication package. The two-party data come from the same saved simulation archive.

## Local peak check

A local peak is an offer outside the bargaining zone for which no change to one issue would increase the number of parties whose reservation values are met. We counted these offers and compared the count with the agreement rates and the gains from wider search in the same saved runs. With one-issue search, peak counts were negatively associated with agreement among six-party and two-party negotiations (Spearman correlations of −.413 and −.446, respectively). The benefit of allowing up to three changes was larger for negotiations with more peaks (correlations of .362 and .405). [Correlations](results/local_peak_correlations.csv) · [Agreement rates by peak count](results/local_peak_agreement_rates.csv) · [Counts by negotiation](results/local_peak_counts.csv)
