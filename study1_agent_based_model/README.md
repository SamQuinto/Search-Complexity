# Study 1 · Agent-based model

The model examines whether incremental search makes it harder to reach agreement as search complexity rises, and whether allowing agents to change more issues at once improves agreement. These comparisons motivate the predictions tested in the empirical studies.

From the repository root, install the [requirements](../requirements.txt) and run:

```bash
python study1_agent_based_model/figures.py
python study1_agent_based_model/replay.py
```

The first command draws both figures and saves the estimates for Figure 2. The second replays the three search conditions for the first negotiation and checks the results against the saved values. Use `--scenarios 1000` to replay all 302,700 simulations. The figures can be rebuilt without running the simulations again.

| File | Contents |
| --- | --- |
| [Figure 1](results/figure_1_search_example.png) | An illustration of how a two-issue revision can reach agreement when neither one-issue revision attracts more acceptance |
| [Figure 2](results/figure_2_simulated_agreement.png) | Agreement rates and the gains from wider search across five levels of search complexity |
| [Figure 2 estimates](results/figure_2_estimates.csv) | Agreement rates and gains in percentage points |
| [Simulation conditions](data/simulation_conditions.csv) | Agreement rate, run count, and structural measures for each negotiation under each search rule |
| [Negotiation inputs](data/negotiations.json.gz) | The generated payoff tables and reservation values |
| [Model code](supporting/negotiation_search_engine.py) | The engine used to produce the saved simulations |

## How the comparison works

The sample includes the first 1,000 generated six-party, ten-issue negotiations by saved scenario index with a nonempty bargaining zone and results for all three search rules. Agents could change one issue, up to two issues, or up to three issues in each counteroffer. The rule for choosing a reference offer, the opening rule, and the stopping rule were the same throughout. On each counteroffer, the agent had a 50% chance of drawing its reference from the group's offer history and otherwise used its own history. Among untried offers within the permitted distance, the agent chose the offer with the highest payoff to itself. The run ended in agreement when it found an offer that met all parties' reservation values.

The saved model treats a payoff equal to the reservation value as acceptable. That same comparison is used to calculate search complexity and bargaining-zone share in this model. Search complexity is the share of offers from which there is no sequence of one-issue changes that continually increases the number of parties whose reservation values are met and ends in agreement. Figure 1 illustrates that measurement idea. It uses four possible packages and three parties, with payoffs (1, 1, −3) at the starting offer, (3, −1, −1) and (−1, 3, −1) at the one-issue alternatives, and (1, 1, 1) when both choices change.

For Figure 2, we rank the negotiations by search complexity, break ties by the saved index, and make five groups of 200 negotiations. Each negotiation gets equal weight. There are 100 simulations per negotiation and search rule, with 1,000 per rule for one negotiation. The same seed sequence is used for a given negotiation across the three rules. The figure shows the average agreement rate under each rule and the difference from one-issue search, in percentage points.

The inputs come from the saved search-distance comparison in the computational model replication package, using the same sample as its search-complexity panel of Figure B2. The deposited inputs include the generated negotiations used here.
