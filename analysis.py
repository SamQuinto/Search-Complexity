"""Study 1 models, uncertainty checks, and machine-readable result tables.

Run through the replication notebook after building the study dataset. This
module never reads a private path or downloads files. The outcome is a fraction
and continuous predictors are standardized within each estimation sample.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


OUTCOME = "agreement_rate"
SC = "search_complexity"
BZ = "bargaining_zone_share"
CONTROLS = [
    "number_of_issues", "number_of_parties", "number_of_compatible_issues",
    "automated_counterpart", "non_unanimous_rule",
]
PREDICTORS = [SC, BZ, *CONTROLS]
CONTINUOUS = [SC, BZ, *CONTROLS[:3]]
MODELS = {
    "bz_controls": [BZ, *CONTROLS],
    "sc_controls": [SC, *CONTROLS],
    "joint": [SC, BZ, *CONTROLS],
    "bz_only": [BZ],
    "sc_only": [SC],
    "weighted_joint": [SC, BZ, *CONTROLS],
}
UNWEIGHTED = [model for model in MODELS if model != "weighted_joint"]
SEED = 20261105


def exercise_key(sample):
    """Use connected exercise IDs when supplied by the dataset builder."""
    return "scenario_cluster" if "scenario_cluster" in sample else "negotiation_scenario"


def structure_sample(structures, strict=False):
    """Use the narrower observed outcome when the strict evidence differs."""
    flag = "strict_eligible" if strict else "main_eligible"
    included = structures[flag].astype(str).str.lower().isin(["true", "1", "yes", "y"])
    sample = structures.loc[included].copy()
    if strict:
        for name in [OUTCOME, "agreements", "negotiations"]:
            sample[name] = sample[f"strict_{name}"]
    return sample


def common_sample(data):
    """Use the same complete rows for both R² models and the joint model."""
    if not data.observation_id.is_unique:
        raise ValueError("An observation ID occurs more than once")
    sample = data.dropna(subset=[OUTCOME, *PREDICTORS]).copy().reset_index(drop=True)
    if len(sample) < 3 or sample[exercise_key(sample)].isna().any():
        raise ValueError("Each sample needs complete exercise IDs and at least three rows")
    if sample[exercise_key(sample)].nunique() < 2:
        raise ValueError("Exercise-clustered inference needs at least two exercise groups")
    for name in [OUTCOME, SC, BZ, *CONTROLS[3:]]:
        if not sample[name].between(0, 1).all():
            raise ValueError(f"{name} must be between zero and one")
    if not (sample[SC] <= 1 - sample[BZ] + 1e-9).all():
        raise ValueError("Search complexity exceeds the fraction of unacceptable offers")
    return sample


def model_sample(sample, model):
    if model == "weighted_joint":
        counts = sample.negotiations
        return sample.loc[counts.notna() & counts.gt(0) & np.isfinite(counts)]
    return sample


def standardize(raw):
    """Apply the same transformation in a fit and in each bootstrap draw."""
    standardized = raw.copy()
    for index, name in enumerate(PREDICTORS):
        if name in CONTINUOUS:
            values = raw[:, index]
            sd = values.std()
            standardized[:, index] = (values - values.mean()) / sd if sd > 1e-12 else 0
    return standardized


def design(standardized, model):
    """Keep focal terms and omit controls that add no independent information."""
    predictors = MODELS[model]
    indices = [PREDICTORS.index(name) for name in predictors]
    full = np.column_stack((np.ones(len(standardized)), standardized[:, indices]))
    names = ["const", *predictors]
    if np.linalg.matrix_rank(full) == full.shape[1]:
        return full, names, []
    keep = [0]
    dropped = []
    for index, name in enumerate(predictors, 1):
        if np.linalg.matrix_rank(full[:, [*keep, index]]) > len(keep):
            keep.append(index)
        elif name in [SC, BZ]:
            raise ValueError(f"{model}: {name} is not estimable in this sample")
        else:
            dropped.append(name)
    return full[:, keep], [names[index] for index in keep], dropped


def coefficient_rows(result, inference, df, unavailable=()):
    rows = []
    intervals = result.conf_int()
    for term, estimate in result.params.items():
        row = {"term": term, "b": estimate, "inference": inference, "df": df}
        if term in unavailable:
            row.update(se=np.nan, p=np.nan, ci_low=np.nan, ci_high=np.nan)
        else:
            row.update(se=result.bse[term], p=result.pvalues[term],
                       ci_low=intervals.loc[term, 0], ci_high=intervals.loc[term, 1])
        rows.append(row)
    return rows


def fit(sample, model):
    """Estimate one model and report HC3 and exercise-clustered CR1 uncertainty."""
    use = model_sample(sample, model)
    if len(use) < 3:
        raise ValueError(f"{model}: too few observations")
    matrix, terms, dropped = design(standardize(use[PREDICTORS].to_numpy(float)), model)
    x = pd.DataFrame(matrix, columns=terms, index=use.index)
    y = use[OUTCOME]
    if x.shape[1] >= len(use) or y.nunique() < 2:
        raise ValueError(f"{model}: insufficient residual degrees of freedom or outcome variation")
    weighted = model == "weighted_joint"
    regression = sm.WLS(y, x, weights=use.negotiations) if weighted else sm.OLS(y, x)
    ordinary = regression.fit()
    groups = use[exercise_key(use)]
    group_sizes = groups.value_counts()
    group_count = len(group_sizes)
    # One indicator can distinguish only one row. It then fits that row exactly
    # and HC3 divides a zero residual by zero. Absorb that row and its indicator
    # for HC3, retaining the full model's estimates and residual degrees of freedom.
    singleton = []
    absorbed = np.zeros(len(x), dtype=bool)
    for name in CONTROLS[3:]:
        if name in x and x[name].nunique() == 2:
            rare = x[name].map(x[name].value_counts()).eq(1).to_numpy()
            if rare.any():
                singleton.append(name)
                absorbed |= rare
    if singleton:
        reduced_x = x.loc[~absorbed].drop(columns=singleton)
        reduced_y = y.loc[~absorbed]
        reduced = sm.WLS(reduced_y, reduced_x, weights=use.negotiations.loc[~absorbed]) if weighted else sm.OLS(reduced_y, reduced_x)
        hc3 = reduced.fit(cov_type="HC3", use_t=True)
        np.testing.assert_allclose(hc3.params, ordinary.params[reduced_x.columns], atol=1e-9)
        critical = stats.t.ppf(.975, ordinary.df_resid)
        rows = []
        for term, estimate in ordinary.params.items():
            se = hc3.bse.get(term, np.nan)
            rows.append({"term": term, "b": estimate, "inference": "HC3",
                         "df": ordinary.df_resid, "se": se,
                         "p": 2 * stats.t.sf(abs(estimate) / se, ordinary.df_resid) if se > 0 else np.nan,
                         "ci_low": estimate - critical * se, "ci_high": estimate + critical * se})
    else:
        hc3 = regression.fit(cov_type="HC3", use_t=True)
        rows = coefficient_rows(hc3, "HC3", ordinary.df_resid)
    if group_count > 1:
        clustered = regression.fit(
            cov_type="cluster", use_t=True,
            cov_kwds={"groups": groups, "use_correction": True, "df_correction": True},
        )
        np.testing.assert_allclose(clustered.params, ordinary.params, atol=1e-10)
        rows.extend(coefficient_rows(clustered, "CR1", group_count - 1, singleton))
    model_info = {
        "model": model, "n": len(use), "scenario_groups": group_count,
        "largest_group": int(group_sizes.max()),
        "r_squared": ordinary.rsquared, "adjusted_r_squared": ordinary.rsquared_adj,
        "dropped_controls": ", ".join(dropped),
        "controls_with_unavailable_uncertainty": ", ".join(singleton),
        "predictions_below_zero": int((ordinary.fittedvalues < 0).sum()),
        "predictions_above_one": int((ordinary.fittedvalues > 1).sum()),
    }
    return pd.DataFrame(rows).assign(model=model, n=len(use), scenario_groups=group_count), model_info


def resample_estimates(raw, y, weights=None):
    """Use least-squares point estimates inside the paired percentile bootstrap."""
    matrix = standardize(raw)
    if weights is None:
        fit_models = UNWEIGHTED
        weights = np.ones(len(y))
    else:
        fit_models = ["weighted_joint"]
    root = np.sqrt(weights)
    total = np.sum(weights * (y - np.average(y, weights=weights)) ** 2)
    estimates = {}
    for model in fit_models:
        try:
            x, names, _ = design(matrix, model)
            if len(y) <= x.shape[1] or total <= 0:
                continue
        except ValueError:
            continue
        b = np.linalg.lstsq(x * root[:, None], y * root, rcond=None)[0]
        r2 = 1 - np.sum(weights * (y - x @ b) ** 2) / total
        estimates[model] = (dict(zip(names, b)), r2)
    output = {}
    for model, name, term in [
        ("joint", "H1", SC), ("weighted_joint", "H1", SC),
        ("bz_only", "bz_unadjusted", BZ), ("sc_only", "sc_unadjusted", SC),
    ]:
        if model in estimates:
            output[name] = float(estimates[model][0][term])
    if {"sc_controls", "bz_controls"}.issubset(estimates):
        output["H2"] = float(estimates["sc_controls"][1] - estimates["bz_controls"][1])
    return output


def bootstrap(sample, draws, seed, by_exercise, weighted):
    """Resample whole exercise groups or study rows using common draws."""
    use = model_sample(sample, "weighted_joint") if weighted else sample
    raw, y = use[PREDICTORS].to_numpy(float), use[OUTCOME].to_numpy(float)
    weights = use.negotiations.to_numpy(float) if weighted else None
    rng = np.random.default_rng(seed)
    groups = list(use.groupby(exercise_key(use), sort=False).indices.values())
    labels = ["H1"] if weighted else ["H1", "H2", "bz_unadjusted", "sc_unadjusted"]
    sampled = {name: [] for name in labels}
    for _ in range(draws):
        if by_exercise:
            selected = rng.integers(0, len(groups), len(groups))
            positions = np.concatenate([groups[index] for index in selected])
        else:
            positions = rng.integers(0, len(use), len(use))
        values = resample_estimates(raw[positions], y[positions],
                                    None if weights is None else weights[positions])
        for name, estimate in values.items():
            if np.isfinite(estimate):
                sampled[name].append(estimate)
    rows = []
    for name, estimates in sampled.items():
        low, high = np.quantile(estimates, [.025, .975]) if estimates else (np.nan, np.nan)
        rows.append({"test": name, "ci_low": low, "ci_high": high,
                     "draws_requested": draws, "draws_completed": len(estimates),
                     "invalid_draws": draws - len(estimates),
                     "passes_interval_rule": low > 0 if name in ["H2", "bz_unadjusted"] else high < 0})
    return pd.DataFrame(rows)


def omission_checks(sample, by_exercise, weighted):
    """Refit after dropping one observation or exercise group at a time."""
    use = model_sample(sample, "weighted_joint") if weighted else sample
    key = exercise_key(use) if by_exercise else "observation_id"
    checks = [("weighted_joint", "H1", SC)] if weighted else [
        ("joint", "H1", SC), ("bz_only", "bz_unadjusted", BZ), ("sc_only", "sc_unadjusted", SC),
    ]
    rows = []
    for omitted in use[key].unique():
        remaining = use.loc[use[key].ne(omitted)]
        for model, name, term in checks:
            try:
                coefficient, _ = fit(remaining, model)
                term_rows = coefficient.loc[coefficient.term.eq(term)].set_index("inference")
                estimate = term_rows.loc["HC3", "b"]
                p_hc3 = term_rows.loc["HC3", "p"]
                p_cluster = term_rows.loc["CR1", "p"] if "CR1" in term_rows.index else np.nan
            except ValueError:
                estimate = p_hc3 = p_cluster = np.nan
            direction = 1 if name == "bz_unadjusted" else -1
            rows.append({"omitted": omitted, "test": name, "n": len(remaining),
                         "estimate": estimate, "p": p_cluster, "p_hc3": p_hc3,
                         "passes": direction * estimate > 0 and p_cluster < .05})
        if not weighted:
            estimates = resample_estimates(remaining[PREDICTORS].to_numpy(float),
                                            remaining[OUTCOME].to_numpy(float))
            delta = estimates.get("H2", np.nan)
            rows.append({"omitted": omitted, "test": "H2", "n": len(remaining),
                         "estimate": delta, "p": np.nan, "p_hc3": np.nan, "passes": delta > 0})
    return pd.DataFrame(rows)


def describe(sample, name):
    variables = [OUTCOME, BZ, SC, *CONTROLS]
    descriptives = sample[variables].agg(["count", "mean", "std", "min", "max"]).T
    descriptives.index.name = "variable"
    correlations = []
    for i, left in enumerate(variables):
        for right in variables[i:]:
            r = p = np.nan
            if sample[left].nunique() > 1 and sample[right].nunique() > 1:
                r, p = stats.pearsonr(sample[left], sample[right])
            correlations.append({"dataset": name, "variable": left, "other_variable": right,
                                 "r": r, "p": p, "n": len(sample)})
    return descriptives.reset_index().assign(dataset=name), pd.DataFrame(correlations)


def exercise_means(sample):
    """Give each named exercise equal weight after averaging its versions."""
    means = sample.groupby(exercise_key(sample), as_index=False)[[OUTCOME, *PREDICTORS]].mean()
    return means.rename(columns={exercise_key(sample): "negotiation_scenario"}).assign(
        observation_id=lambda x: x.negotiation_scenario
    )


def run_analysis(studies, structures, output_dir, draws=5000):
    """Write CSV results and sample counts from the linked study and structure inputs.

    The structural input contains only eligible versions with an identifiable
    study. It includes strict eligibility flags and the corresponding outcome
    and count fields. Only the study sample determines the two main decisions.
    """
    if draws < 1:
        raise ValueError("At least one bootstrap draw is required")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = {
        "study": common_sample(studies),
        "structure": common_sample(structure_sample(structures)),
        "strict_structure": common_sample(structure_sample(structures, strict=True)),
    }
    averaging_samples = {
        "exercise_mean": exercise_means(samples["structure"]),
        "strict_exercise_mean": exercise_means(samples["strict_structure"]),
    }
    table_names = [
        "coefficients", "model_fit", "descriptive_statistics", "correlations",
        "bootstrap_intervals", "omission_checks", "hypothesis_tests",
    ]
    tables = {name: [] for name in table_names}
    sample_summary = {}
    for offset, (name, sample) in enumerate({**samples, **averaging_samples}.items()):
        print(f"{name}: {len(sample)} complete observations", flush=True)
        sizes = sample[exercise_key(sample)].value_counts()
        sample_summary[name] = {"n": len(sample), "exercise_groups": len(sizes),
                                "largest_group": int(sizes.max())}
        coefficients, models = [], []
        for model in (MODELS if name in samples else UNWEIGHTED):
            terms, info = fit(sample, model)
            coefficients.append(terms)
            models.append(info)
        coefficients = pd.concat(coefficients, ignore_index=True)
        model_fit = pd.DataFrame(models)
        tables["coefficients"].append(coefficients.assign(dataset=name))
        tables["model_fit"].append(model_fit.assign(dataset=name))
        descriptives, correlations = describe(sample, name)
        tables["descriptive_statistics"].append(descriptives)
        tables["correlations"].append(correlations)
        if name not in samples:
            continue

        # Confirm the fast bootstrap fits reproduce the full-sample estimates.
        fast = resample_estimates(sample[PREDICTORS].to_numpy(float), sample[OUTCOME].to_numpy(float))
        fit_r2 = model_fit.set_index("model").r_squared
        delta = fit_r2["sc_controls"] - fit_r2["bz_controls"]
        joint = coefficients.loc[
            coefficients.model.eq("joint") & coefficients.term.eq(SC) & coefficients.inference.eq("CR1")
        ].iloc[0]
        np.testing.assert_allclose([fast["H1"], fast["H2"]], [joint.b, delta], atol=1e-10)
        for by_exercise in [False, True]:
            for weighted in [False, True]:
                kind = ("exercise" if by_exercise else "observation") + ("_weighted" if weighted else "")
                seed = SEED + offset + 100 * int(by_exercise) + 200 * int(weighted)
                intervals = bootstrap(sample, draws, seed, by_exercise, weighted)
                omissions = omission_checks(sample, by_exercise, weighted)
                tables["bootstrap_intervals"].append(intervals.assign(dataset=name, resampling=kind, seed=seed))
                tables["omission_checks"].append(omissions.assign(dataset=name, omission=kind))
                if by_exercise and not weighted:
                    h2 = intervals.loc[intervals.test.eq("H2")].iloc[0]
        decisions = [
            {"hypothesis": "H1", "estimate": joint.b, "se": joint.se, "p": joint.p,
             "ci_low": joint.ci_low, "ci_high": joint.ci_high,
             "inference": "CR1", "supported": joint.b < 0 and joint.p < .05},
            {"hypothesis": "H2", "estimate": delta, "se": np.nan, "p": np.nan,
             "ci_low": h2.ci_low, "ci_high": h2.ci_high,
             "inference": "paired exercise bootstrap", "supported": delta > 0 and h2.ci_low > 0},
        ]
        tables["hypothesis_tests"].append(pd.DataFrame(decisions).assign(
            dataset=name, primary=name == "study", n=len(sample), scenario_groups=len(sizes)
        ))

    result = {name: pd.concat(parts, ignore_index=True) for name, parts in tables.items()}
    ranks = []
    for predictor in [BZ, SC]:
        rho, p = stats.spearmanr(samples["study"][predictor], samples["study"][OUTCOME])
        ranks.append({"dataset": "study", "predictor": predictor, "spearman_rho": rho,
                      "p": p, "n": len(samples["study"])})
    result["rank_correlations"] = pd.DataFrame(ranks)
    for name, table in result.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)
    (output_dir / "analysis_summary.json").write_text(
        json.dumps({"bootstrap_draws": draws, "base_seed": SEED, "samples": sample_summary}, indent=2),
        encoding="utf-8",
    )
    summary = {
        "bootstrap_draws": draws,
        "base_seed": SEED,
        "samples": sample_summary,
        "hypothesis_tests": json.loads(result["hypothesis_tests"].to_json(orient="records")),
        "model_fit": json.loads(result["model_fit"].to_json(orient="records")),
        "bootstrap_intervals": json.loads(result["bootstrap_intervals"].to_json(orient="records")),
    }
    (output_dir / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return result


if __name__ == '__main__':
    from prepare_data import build_data
    from presentation import build_presentation

    root = Path(__file__).resolve().parent
    output = root / 'outputs'
    studies, structures, flow = build_data(root, output)
    tables = run_analysis(studies, structures, output)
    build_presentation(studies, tables, flow, output)
