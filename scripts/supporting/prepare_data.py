"""Build one observation per experiment from the released coded evidence.

The source files are transcribed evidence. This script checks their links and
counts, applies the documented inclusion decisions, and combines conditions.
It does not infer missing reservation values or change an observed outcome.
"""

from pathlib import Path

import numpy as np
import pandas as pd


MEASURES = ['search_complexity', 'bargaining_zone_share']
CONTROLS = ['number_of_issues', 'number_of_parties', 'number_of_compatible_issues',
            'automated_counterpart', 'non_unanimous_rule']
PREDICTORS = [*MEASURES, *CONTROLS]
MODEL_COLUMNS = ['observation_id', 'agreement_rate', 'negotiations', *PREDICTORS]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def distinct_text(values):
    return ' | '.join(dict.fromkeys(str(value) for value in values.dropna() if str(value)))


def weights_for(rows):
    """Use encounter counts only when every component has a positive count."""
    complete = rows.negotiations.notna().all() and rows.negotiations.gt(0).all()
    counts = rows.negotiations.to_numpy(float) if complete else np.ones(len(rows))
    return counts / counts.sum(), bool(complete)


def combine_study_components(components):
    records = []
    for study_id, rows in components.groupby('study_id', sort=False):
        weights, complete_counts = weights_for(rows)
        exact_counts = complete_counts and rows.agreements.notna().all()
        negotiations = rows.negotiations.sum() if complete_counts else np.nan
        agreements = rows.agreements.sum() if exact_counts else np.nan
        rate = agreements / negotiations if exact_counts else float(np.dot(weights, rows.agreement_rate))
        first = rows.iloc[0]
        require(rows.paper_citation.nunique() == 1 and rows.study_label.nunique() == 1,
                f'{study_id} has conflicting study identifiers')
        records.append({
            'observation_id': study_id,
            'paper_citation': first.paper_citation,
            'study_label': first.study_label,
            'negotiation_exercise': distinct_text(rows.negotiation_exercise),
            'payoff_ids': distinct_text(rows.payoff_id),
            'component_ids': distinct_text(rows.component_id),
            'component_count': len(rows),
            'agreement_rate': rate,
            'agreements': agreements,
            'negotiations': negotiations,
            'aggregation': ('Single observed component' if len(rows) == 1 else
                            'Encounter-count weighted components' if complete_counts else
                            'Equal weights across documented components'),
            **{name: float(np.dot(weights, rows[name])) for name in PREDICTORS},
            'payoff_source': distinct_text(rows.payoff_source),
            'reservation_values_or_rule': distinct_text(rows.reservation_values_or_rule),
            'agreement_rate_source': distinct_text(rows.agreement_rate_source),
            'agreement_rate_coding': distinct_text(rows.agreement_rate_coding),
            'source_link': distinct_text(rows.source_link),
            'strict_reason': distinct_text(rows.strict_reason),
            'approval_rule': distinct_text(rows.approval_rule),
            'approval_rule_basis': distinct_text(rows.approval_rule_basis),
            'approval_rule_source': distinct_text(rows.approval_rule_source),
        })
    return pd.DataFrame(records)


def aggregate_identical_structures(components):
    """Give independent experiments equal weight within a coded structure.

    First combine multiple components for the same experiment and structure.
    Then average those experiment rates. This keeps an experiment with a larger
    sample from receiving more weight in this supplementary comparison.
    """
    records = []
    for payoff_id, rows in components.groupby('payoff_id', sort=False):
        experiments = combine_study_components(rows)
        first = rows.iloc[0]
        fixed = [*MEASURES, *CONTROLS[:3], 'non_unanimous_rule']
        require(rows[fixed].nunique().le(1).all(),
                f'{payoff_id} does not have a single set of predictors')
        records.append({
            'observation_id': payoff_id,
            'negotiation_exercise': first.negotiation_exercise,
            'agreement_rate': experiments.agreement_rate.mean(),
            'contributing_experiments': len(experiments),
            **{name: experiments[name].mean() for name in PREDICTORS},
        })
    return pd.DataFrame(records)


def build_data(root, output_dir):
    root, output_dir = Path(root), Path(output_dir)
    source = root / 'data/sources'
    outcomes = pd.read_csv(source / 'study_outcomes.csv').rename(
        columns={'structure_id': 'payoff_id', 'negotiation_scenario': 'negotiation_exercise'})
    structures = pd.read_csv(source / 'structure_inputs.csv').rename(columns={'observation_id': 'payoff_id'})
    scores = pd.read_csv(source / 'structural_scores.csv').rename(columns={'observation_id': 'payoff_id'})
    decisions = pd.read_csv(root / 'data/component_decisions.csv', keep_default_na=False)
    from .payoff_metrics import (calculate_payoff_file, replay_acceptance_inputs,
                                calculate_acceptability_proofs, calculate_programmed_rules,
                                calculate_catalog_inputs)

    metric_records = []
    for calculated in replay_acceptance_inputs(source):
        matches = scores.payoff_id.eq(calculated['payoff_id'])
        require(matches.sum() == 1, 'An acceptance input needs one matching payoff ID')
        for measure in MEASURES:
            require(np.isclose(scores.loc[matches, measure].iloc[0], calculated[measure], atol=1e-12, rtol=0),
                    f'The replayed {measure} differs from its recorded value')
            scores.loc[matches, measure] = calculated[measure]
        metric_records.append(calculated)
    for path in sorted((root / 'data/payoff_schedules').glob('*.json')):
        calculated = calculate_payoff_file(path)
        matches = scores.payoff_id.eq(calculated['payoff_id'])
        require(matches.sum() == 1, 'A numerical schedule needs one matching payoff ID')
        for measure in MEASURES:
            require(np.isclose(scores.loc[matches, measure].iloc[0], calculated[measure], atol=1e-12, rtol=0),
                    f'The recalculated {measure} differs from its recorded value')
            scores.loc[matches, measure] = calculated[measure]
        structural_match = structures.payoff_id.eq(calculated['payoff_id'])
        for control in CONTROLS[:3]:
            require(np.isclose(structures.loc[structural_match, control].iloc[0], calculated[control]),
                    f'The numerical schedule disagrees with {control}')
        metric_records.append(calculated)
    for calculated in calculate_acceptability_proofs(root / 'data/acceptability_proofs.json'):
        matches = scores.payoff_id.eq(calculated['payoff_id'])
        require(matches.sum() == 1, 'An acceptability proof needs one matching payoff ID')
        for measure in MEASURES:
            require(np.isclose(scores.loc[matches, measure].iloc[0], calculated[measure], atol=1e-12, rtol=0),
                    f'The source proof disagrees with the recorded {measure}')
            scores.loc[matches, measure] = calculated[measure]
        metric_records.append(calculated)
    for calculated in calculate_programmed_rules(root / 'data/programmed_acceptance_rules.json'):
        matches = scores.payoff_id.eq(calculated['payoff_id'])
        require(matches.sum() == 1, 'A programmed rule needs one matching payoff ID')
        for measure in MEASURES:
            require(np.isclose(scores.loc[matches, measure].iloc[0], calculated[measure], atol=1e-12, rtol=0),
                    f'The programmed rule disagrees with the recorded {measure}')
            scores.loc[matches, measure] = calculated[measure]
        metric_records.append(calculated)
    catalog_values, catalog_components = calculate_catalog_inputs(
        root / 'data/raw_payoff_catalog.json', structures, root / 'data/within_payoff_weights.csv')
    for calculated in catalog_values:
        matches = scores.payoff_id.eq(calculated['payoff_id'])
        require(matches.sum() == 1, 'A payoff table needs one matching payoff ID')
        for measure in MEASURES:
            require(np.isclose(scores.loc[matches, measure].iloc[0], calculated[measure], atol=1e-12, rtol=0),
                    f'The numerical table for {calculated["payoff_id"]} disagrees with {measure}')
            scores.loc[matches, measure] = calculated[measure]
        metric_records.append(calculated)
    # A few source tasks use payoff functions, continuous issues, or a graph
    # too large to enumerate. Replay their recorded grids and sampling rules.
    # These checks never substitute a newly chosen grid or a different seed.
    from .source_functions import calculate_formula_inputs
    from .additional_functions import calculate_additional_inputs
    from .sampled_metrics import calculate_player_input

    function_values = calculate_formula_inputs(root) + calculate_additional_inputs(root)
    player_value, player_components = calculate_player_input(root / 'data/raw_payoff_catalog.json')
    for calculated in [*function_values, player_value]:
        matches = scores.payoff_id.eq(calculated['payoff_id'])
        require(matches.sum() == 1, 'A source function needs one matching payoff ID')
        for measure in MEASURES:
            require(np.isclose(scores.loc[matches, measure].iloc[0], calculated[measure],
                               atol=1e-12, rtol=0),
                    f'The source function for {calculated["payoff_id"]} disagrees with {measure}')
        metric_records.append(calculated)
    require(outcomes.component_id.is_unique, 'Duplicate source outcome component')
    require(structures.payoff_id.is_unique and scores.payoff_id.is_unique,
            'Duplicate structural record')
    require(decisions.component_id.is_unique and
            set(decisions.component_id) == set(outcomes.component_id),
            'Every outcome needs one explicit inclusion decision')

    structures = structures.merge(scores, on='payoff_id', validate='one_to_one')
    columns = ['payoff_id', *PREDICTORS, 'main_eligible', 'payoff_source',
               'reservation_values_or_rule']
    components = outcomes.merge(structures[columns], on='payoff_id', how='left', validate='many_to_one')
    components = components.merge(
        decisions[['component_id', 'main_included', 'participant_sample_identified',
                   'strict_included', 'strict_reason', 'strict_evidence']],
        on='component_id', validate='one_to_one')
    components = components.loc[components.main_included.eq('Y')].copy()
    metric_records = list({record['payoff_id']: record for record in metric_records}.values())
    replayed = {record['payoff_id'] for record in metric_records}
    for payoff_id in components.payoff_id.unique():
        if payoff_id not in replayed:
            row = structures.loc[structures.payoff_id.eq(payoff_id)].iloc[0]
            metric_records.append({'payoff_id': payoff_id,
                                   'bargaining_zone_share': row.bargaining_zone_share,
                                   'search_complexity': row.search_complexity,
                                   'input_type': 'Recorded score with source note',
                                   'source': row.payoff_source})
    for record in metric_records:
        record['recomputed_from_included_input'] = record['payoff_id'] in replayed
    require(set(components.payoff_id).issubset(replayed),
            'Every included payoff ID needs a reproducible metric input')
    require(components.main_eligible.eq(True).all(), 'An outcome links to an excluded structure')
    require(components[PREDICTORS].notna().all().all(), 'A predictor is missing')
    require(components.agreement_rate.between(0, 1).all(), 'An agreement rate is outside 0–1')
    counted = components.agreements.notna() & components.negotiations.notna()
    require(np.allclose(components.loc[counted, 'agreement_rate'],
                        components.loc[counted, 'agreements'] / components.loc[counted, 'negotiations'],
                        atol=1e-10, rtol=0), 'Agreement counts disagree with the recorded rate')
    require(components.loc[counted, 'negotiations'].gt(0).all(), 'Invalid encounter denominator')
    require(components.loc[counted, 'agreements'].between(
        0, components.loc[counted, 'negotiations']).all(), 'Invalid agreement count')
    require(components.participant_sample_identified.eq('Y').all() and
            components[['study_id', 'paper_citation', 'study_label']].notna().all().all(),
            'Every observation needs an identified participant sample and research source')
    components['strict_included'] = components.strict_included.eq('Y')
    components['agreement_rate_coding'] = np.where(
        counted, 'Calculated from retained agreement and negotiation counts',
        'Reported rate; an exact agreement numerator is not available')
    residual = components.payoff_id.eq('market_alternatives_remaining_13_pooled')
    components.loc[residual, 'agreement_rate_coding'] = 'Derived from exact residual counts (270/276)'
    reviewed = components.payoff_id.eq('van_den_abbeele_two_power_versions_pooled')
    components.loc[reviewed, 'agreement_rate_coding'] = 'Matched meta-analysis counts (90/104)'
    components.loc[reviewed, 'agreement_rate_source'] = (
        'Warsitzka et al. (2024), replication-data row W0422, Van den Abbeele et al. (2009), '
        'Study 1: 90 agreements and 104 negotiations. https://osf.io/2c9gf/. '
        'The original paper reports 104 dyads and outside-option/timeout information, '
        'but does not state this agreement numerator unambiguously.')

    corrections = pd.read_csv(root / 'data/control_corrections.csv')
    for correction in corrections.itertuples(index=False):
        require(correction.variable in CONTROLS, 'Only documented control corrections are allowed here')
        matches = components.component_id.eq(correction.component_id)
        require(matches.sum() == 1, 'A control correction must identify exactly one component')
        require(np.isclose(components.loc[matches, correction.variable].iloc[0], correction.recorded_value),
                'The recorded control differs from the correction audit')
        components.loc[matches, correction.variable] = correction.corrected_value

    # Keep the readable approval rule beside its numeric control. Unanimity is
    # the default unless the study or matching exercise specifies another rule.
    approval = pd.read_csv(root / 'data/approval_rules.csv')
    require(approval.payoff_id.is_unique, 'Each payoff record needs one approval-rule description')
    approval = approval.rename(columns={'coding_basis': 'approval_rule_basis',
                                        'source': 'approval_rule_source'})
    components = components.merge(
        approval[['payoff_id', 'approval_rule', 'approval_rule_basis',
                  'approval_rule_source', 'non_unanimous_share']],
        on='payoff_id', how='left', validate='many_to_one')
    require(components.approval_rule.notna().all(), 'An approval-rule description is missing')
    require(np.allclose(components.non_unanimous_rule, components.non_unanimous_share,
                        atol=1e-12, rtol=0), 'The approval rule disagrees with the regression control')

    components['main_weight'] = np.nan
    components['strict_weight'] = np.nan
    for _, rows in components.groupby('study_id', sort=False):
        components.loc[rows.index, 'main_weight'] = weights_for(rows)[0]
        retained = rows.loc[rows.strict_included]
        if len(retained):
            components.loc[retained.index, 'strict_weight'] = weights_for(retained)[0]

    main = combine_study_components(components)
    strict_components = components.loc[components.strict_included].copy()
    strict = combine_study_components(strict_components)
    require(main.observation_id.is_unique and strict.observation_id.is_unique,
            'Experiments are duplicated after aggregation')
    require(set(strict.observation_id).issubset(main.observation_id),
            'The strict sample contains a new experiment')

    eligibility = make_eligibility_table(components)
    aggregates = {'aggregate_main': aggregate_identical_structures(components),
                  'aggregate_strict': aggregate_identical_structures(strict_components)}

    save_analysis_files(main, strict, aggregates, components, eligibility, output_dir)
    pd.DataFrame(metric_records).to_csv(output_dir / 'payoff_metric_checks.csv', index=False)
    catalog_components.to_csv(output_dir / 'catalog_component_metrics.csv', index=False)
    pd.DataFrame(player_components).to_csv(output_dir / 'player_component_metrics.csv', index=False)
    return {'main': main, 'strict': strict, **aggregates}

def make_eligibility_table(components):
    """Describe the conditions retained for strict inclusion."""
    audit = []
    for study_id, rows in components.groupby('study_id', sort=False):
        retained = rows.loc[rows.strict_included]
        complete = len(retained) == len(rows)
        audit.append({
            'observation_id': study_id,
            'paper_citation': rows.paper_citation.iloc[0],
            'study_label': rows.study_label.iloc[0],
            'negotiation_exercise': distinct_text(rows.negotiation_exercise),
            'strict_included': 'Y' if len(retained) else 'N',
            'strict_coverage': 'All eligible conditions' if complete else
                               'Recoverable subset of conditions' if len(retained) else
                               'No conditions meet the stricter evidence rule',
            'main_component_count': len(rows),
            'strict_component_count': len(retained),
            'main_negotiations': rows.negotiations.sum() if rows.negotiations.notna().all() else np.nan,
            'strict_negotiations': retained.negotiations.sum() if len(retained) and
                                   retained.negotiations.notna().all() else np.nan,
            'excluded_component_ids': distinct_text(rows.loc[~rows.strict_included, 'component_id']),
            'reason': distinct_text(rows.loc[~rows.strict_included, 'strict_reason']) if not complete
                      else distinct_text(retained.strict_reason),
        })
    eligibility = pd.DataFrame(audit)
    return eligibility


def save_analysis_files(main, strict, aggregates, components, eligibility, output_dir):
    """Save the analysis datasets and their source links."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    main.to_csv(output_dir / 'study_inputs.csv', index=False)
    main[MODEL_COLUMNS].to_csv(output_dir / 'regression_data.csv', index=False)
    strict.to_csv(output_dir / 'strict_study_inputs.csv', index=False)
    strict[MODEL_COLUMNS].to_csv(output_dir / 'strict_regression_data.csv', index=False)
    eligibility.to_csv(output_dir / 'observation_eligibility.csv', index=False)
    for name, data in aggregates.items():
        data.to_csv(output_dir / f'{name}.csv', index=False)
    public_columns = ['component_id', 'study_id', 'paper_citation', 'study_label', 'payoff_id',
                      'negotiation_exercise', 'agreement_rate', 'agreements', 'negotiations',
                      *PREDICTORS, 'payoff_source', 'reservation_values_or_rule',
                      'agreement_rate_source', 'agreement_rate_coding', 'source_link', 'strict_included', 'strict_reason',
                      'strict_evidence', 'main_weight', 'strict_weight', 'approval_rule',
                      'approval_rule_basis', 'approval_rule_source']
    components[public_columns].to_csv(output_dir / 'component_evidence.csv', index=False)


def prepare_analysis_data(root, output_dir):
    """Load the main dataset and construct the supplementary analysis datasets.

    The condition records already contain the coded structural measures. We
    do not need to recalculate the payoff tables to reproduce the findings.
    """
    root, output_dir = Path(root), Path(output_dir)
    released = pd.read_csv(root / 'data/regression_data.csv')
    components = pd.read_csv(root / 'data/derived/component_evidence.csv')
    require(released.observation_id.is_unique, 'The main dataset has repeated observation IDs.')
    require(components.component_id.is_unique, 'The condition records have repeated IDs.')
    require(components.strict_included.isin([True, False]).all(), 'A strict-inclusion decision is missing.')

    # Recalculate the weights rather than relying on the saved weight columns.
    components['main_weight'] = np.nan
    components['strict_weight'] = np.nan
    for _, rows in components.groupby('study_id', sort=False):
        components.loc[rows.index, 'main_weight'] = weights_for(rows)[0]
        retained = rows.loc[rows.strict_included]
        if len(retained):
            components.loc[retained.index, 'strict_weight'] = weights_for(retained)[0]

    rebuilt = combine_study_components(components)
    expected = released.sort_values('observation_id').reset_index(drop=True)
    actual = rebuilt[MODEL_COLUMNS].sort_values('observation_id').reset_index(drop=True)
    require(expected.observation_id.equals(actual.observation_id),
            'The condition records do not reproduce the main observations.')
    np.testing.assert_allclose(expected.iloc[:, 1:], actual.iloc[:, 1:],
                               atol=1e-12, rtol=0, equal_nan=True)

    strict_components = components.loc[components.strict_included].copy()
    strict = combine_study_components(strict_components)
    aggregates = {'aggregate_main': aggregate_identical_structures(components),
                  'aggregate_strict': aggregate_identical_structures(strict_components)}
    eligibility = make_eligibility_table(components)
    save_analysis_files(rebuilt, strict, aggregates, components, eligibility, output_dir)
    # Keep the released primary dataset as the actual primary regression input.
    released.to_csv(output_dir / 'regression_data.csv', index=False)
    return {'main': released, 'strict': strict, **aggregates}

