# Coded source evidence

| File | Unit and contents |
| --- | --- |
| `study_outcomes.csv` | One coded outcome component. Study and structure IDs, citation, observed rate and counts, and provenance. |
| `structure_inputs.csv` | One coded structure. Exercise and version, payoff source, reservation rule, controls and eligibility. The stricter outcome fields support the version-level sensitivity analysis. |
| `structural_scores.csv` | Recorded bargaining-zone size and search complexity for every structural record. |
| `coding_evidence.csv` | Calculation method, version matching, aggregation and audit notes keyed by structural ID. |
| `metric_input_manifest.csv` | Dimensions, decision rules and provenance for the executable metric inputs. |
| `acceptance_inputs.npz` | Compact party-acceptance arrays for the documented offer grids. |
| `metric_source_corrections.csv` | Source evidence for two corrected links between payoff inputs and the structural records. |

The outcomes join to the structural files using `structure_id` in the outcome file and `observation_id` in the structure files. Source paper links are in the inventory crosswalk. A structural source can differ from the paper reporting the agreement outcome.

For metric replay, code counts acceptances on the grid and traces all strictly improving one-issue paths. A comparison against the recorded scores is written to `outputs/metric_reproduction.csv`. The source and calculation notes support audits of recorded scores. Proprietary role and scoring materials stay in their licensed libraries. The public acceptance arrays contain boolean acceptances for offers, with dimensions and approval thresholds in the manifest.

Run `python replay_metrics.py` from the repository folder for a separate calculation audit in `outputs/`. A discrepancy stops verification and identifies the structure requiring review.

The arrays reproduce 32 of the 104 coded structural records, including 31 of the 102 records linked to the study data. The other 72 coded records enter through their recorded scores. The study-level dataset is reproducible from this combination of replayed and recorded scores.
