# Study 3 · Prolific experiment

Study 3 compares two versions of a three-person office-sharing negotiation. Each version has three roles and nine Include/Exclude decisions. The conditions use identical role narratives, the same bargaining-zone share, and different payoff tables.

| File | Empirica setting |
| --- | --- |
| [Low-complexity negotiation](study3_low_search_complexity.json) | `roleDataURL` for the low condition |
| [High-complexity negotiation](study3_high_search_complexity.json) | `roleDataURL` for the high condition |
| [Post-task survey](post_task_survey.yaml) | `surveyURL` for both conditions |

Use the raw file links for the two treatments. Both use `playerCount: 3`, `readRoleTime: 300`, and `scoringMode: table`. Configure the app to assign one person to each role, display only their own role and payoff table, and record the condition, complete offers, and decisions. Agreement requires all three participants to accept the same offer and receive more than zero points from it.

The survey has one page with two five-point ratings and optional task feedback. Run `python study3_experiment/validate_materials.py` to check both payoff files and recalculate the structural measures. A three-person walkthrough can check the survey and agreement rules in Empirica.
