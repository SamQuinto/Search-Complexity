# Paper and exercise inventories

`paper_inventory.csv` gives one row per candidate paper. `paper_id` links to the starting registry and `paper_study_links.csv`. Search sources can overlap. Retrieval status, documented reason, eligibility evidence, observed outcomes and the number of studies contributed appear in separate columns.

The inventory marks 347 of 370 papers recovered. Four of the 23 remaining papers have a paper-specific note in the retrieval records. The other 19 have only an inventory status. The 347 is the recorded retrieval count. The current local library contains 341 PDFs, and its filenames have yet to be reconciled one-to-one with that count.

`paper_study_links.csv` contains one row per study. It connects each of the 141 study IDs to one of 112 paper IDs. The paper supplying the outcome may differ from the source of the payoff schedule. `source_frequencies.csv` shows both overlapping counts by source and mutually exclusive combinations. The screening records consulted Schweinsberg et al. (2022). The inventory supplies no separate lead tag for that review.

`exercise_inventory.csv` keeps exact normalized exercise and version names from the coded structures, historical candidate records, teaching library and retrieval leads. It records the provider or evidence where known, source and retrieval status, and links to studies with observed agreement rates. The 502 entries include aliases and historical leads. The current study inputs use 66 recorded names.

`starting_study_registry.csv` preserves the 479 starting records and their paper links. Those rows count screening records, which can be individual study conditions. They serve as the fixed reference for the original stopping rule.

The registry has eight preliminary-analysis flags. Several rows link to pooled observations or multiple payoff versions. Harborco and Sale of a Café supply two further preliminary observations outside this registry, producing the original ten-observation comparison.

The starting registry preserves source citations as recorded. Corrected working paper links are supplied in `paper_inventory.csv`.

Four identifier column names were simplified for the code. All 479 registry rows and their cell values are preserved.
