# Study 3 · Prolific experiment

Study 3 compares two versions of a three-person office-sharing negotiation. Each version has three roles and nine Include/Exclude decisions. The conditions use identical role narratives, the same bargaining-zone share, and different payoff tables.

| File | Empirica setting |
| --- | --- |
| [Easy · low search complexity](study3_low_search_complexity.json) | `roleDataURL` for the low condition |
| [Hard · high search complexity](study3_high_search_complexity.json) | `roleDataURL` for the high condition |
| [Post-task survey](post_task_survey.yaml) | `surveyURL` for both conditions |

Use the raw file links for the two treatments. The JSONs follow the [three-person Empirica example](https://raw.githubusercontent.com/SamQuinto/Describing-Search-in-Negotiations/refs/heads/main/shared_office_3p_easy.json), with a `roles` list, a `scoresheet` for each role, and shared `tips`. Easy uses the selected payoff table `4a93c0a77674` (82.23% search complexity) and Hard uses `61024eb53d22` (86.72%). Both give four mutually acceptable offers out of 512.

The JSON scores are rounded to two decimal places. The largest individual agreement payoff is £11.25 in both conditions. Every agreement gives everyone at least £1. The [payoff scaling record](payoff_scaling.md) gives the multipliers and rounding procedure. We checked all 512 offers and verified each party's acceptance decisions and routes to agreement.

Set the app to assign one person to each of the three roles and show each person their own payoff table. The study uses five minutes of preparation. Agreement requires all three participants to accept the same offer and receive more than zero points from it.

The survey has one page with two five-point ratings and optional task feedback. Run `python study3_experiment/validate_materials.py` to check both payoff files and recalculate the structural measures. A three-person walkthrough can check the survey and agreement rules in Empirica.
