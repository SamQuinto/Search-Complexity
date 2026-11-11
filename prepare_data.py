"""Build the study analysis file from coded sources and structural measures."""
from pathlib import Path

import numpy as np
import pandas as pd


CONTROLS = ['number_of_issues', 'number_of_parties', 'number_of_compatible_issues',
            'automated_counterpart', 'non_unanimous_rule']
MEASURES = ['bargaining_zone_share', 'search_complexity']
REGRESSION_COLUMNS = ['observation_id', 'negotiation_scenario', 'scenario_cluster',
                      'agreement_rate', 'negotiations', *MEASURES, *CONTROLS]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def values(series):
    """Retain source strings in their first recorded order."""
    return ' | '.join(dict.fromkeys(str(value) for value in series.dropna() if str(value)))


def encounter_weights(rows):
    counts = rows['negotiations']
    complete = bool(counts.notna().all() and counts.gt(0).all())
    weights = counts.to_numpy(float) if complete else np.ones(len(rows))
    return weights / weights.sum(), complete


def exercise_groups(components):
    """Join exercises used together within one study into connected groups."""
    parents = {name: name for name in components['negotiation_scenario'].unique()}

    def representative(name):
        while parents[name] != name:
            name = parents[name]
        return name

    for _, rows in components.groupby('study_id', sort=False):
        names = rows['negotiation_scenario'].unique()
        for name in names[1:]:
            parents[representative(name)] = representative(names[0])

    return {name: representative(name) for name in parents}


def study_observations(components, structures):
    """Join every source component to its structure and combine within samples."""
    require(components['component_id'].is_unique, 'Duplicate outcome component ID')
    require(components[['study_id', 'structure_id', 'negotiation_scenario']].notna().all().all(),
            'Study, structure and exercise IDs are required')
    require(structures['observation_id'].is_unique, 'Duplicate structure ID')
    require(components['agreement_rate'].between(0, 1).all(), 'Invalid outcome rate')
    known = components['agreements'].notna() & components['negotiations'].notna()
    counted = components.loc[known]
    require(counted['negotiations'].gt(0).all() and
            counted['agreements'].ge(0).all() and
            counted['agreements'].le(counted['negotiations']).all(), 'Invalid agreement counts')
    require(np.allclose(counted['agreement_rate'],
                        counted['agreements'] / counted['negotiations'], atol=1e-10, rtol=0),
            'An exact agreement count differs from the coded rate')

    columns = ['observation_id', *MEASURES, *CONTROLS, 'main_eligible',
               'payoff_source', 'reservation_values_or_rule', 'scenario_version']
    joined = components.merge(structures[columns], left_on='structure_id', right_on='observation_id',
                              how='left', validate='many_to_one')
    require(joined[[*MEASURES, *CONTROLS]].notna().all().all(),
            'Some study outcomes lack a complete structural match')
    require(joined['main_eligible'].eq(True).all(), 'An ineligible structure is linked to a study')
    require(joined[MEASURES].apply(lambda col: col.between(0, 1)).all().all(),
            'Structural measures must be proportions')

    groups = exercise_groups(joined)
    records = []
    joined['within_study_weight'] = np.nan
    for study_id, rows in joined.groupby('study_id', sort=False):
        first = rows.iloc[0]
        require(rows['paper_citation'].nunique(dropna=False) == 1 and
                rows['study_label'].nunique(dropna=False) == 1,
                f'Conflicting study labels for {study_id}')
        weights, complete = encounter_weights(rows)
        joined.loc[rows.index, 'within_study_weight'] = weights
        exact = complete and rows['agreements'].notna().all()
        total = rows['negotiations'].sum() if complete else np.nan
        agreements = rows['agreements'].sum() if exact else np.nan
        rate = agreements / total if exact else np.dot(weights, rows['agreement_rate'])
        records.append({
            'observation_id': study_id,
            'paper_citation': first['paper_citation'],
            'study_label': first['study_label'],
            'negotiation_scenario': values(rows['negotiation_scenario']),
            'scenario_cluster': groups[first['negotiation_scenario']],
            'structure_ids': values(rows['structure_id']),
            'component_ids': values(rows['component_id']),
            'agreement_rate': rate,
            'agreements': agreements,
            'negotiations': total,
            'aggregation': ('Single source component' if len(rows) == 1 else
                            'Negotiation counts' if complete else 'Equal weights across components'),
            'component_count': len(rows),
            'structure_count': rows['structure_id'].nunique(),
            **{name: float(np.dot(weights, rows[name])) for name in [*MEASURES, *CONTROLS]},
            'payoff_source': values(rows['payoff_source']),
            'reservation_values_or_rule': values(rows['reservation_values_or_rule']),
            'agreement_rate_source': values(rows['agreement_rate_source']),
            'structure_source_link': values(rows['source_link']),
            'coding_note': values(rows['coding_note']),
        })
    return pd.DataFrame.from_records(records), joined


def version_observations(components, structures):
    """Rebuild the linked version-level comparison from independent study rates."""
    results = []
    for structure_id, rows in components.groupby('structure_id', sort=False):
        study_rates = []
        for _, study_rows in rows.groupby('study_id', sort=False):
            weights, _ = encounter_weights(study_rows)
            study_rates.append(np.dot(weights, study_rows['agreement_rate']))
        _, complete = encounter_weights(rows)
        results.append({
            'observation_id': structure_id,
            'agreement_rate': float(np.mean(study_rates)),
            'negotiations': rows['negotiations'].sum() if complete else np.nan,
            'agreements': rows['agreements'].sum() if complete and rows['agreements'].notna().all() else np.nan,
            'contributing_studies': len(study_rates),
        })
    outcome = pd.DataFrame.from_records(results)
    prior_outcome_cols = ['agreement_rate', 'negotiations', 'agreements']
    return outcome.merge(structures.drop(columns=prior_outcome_cols), on='observation_id',
                         how='left', validate='one_to_one')


def flow_table(papers, registry, studies, components, structures, regressions):
    """Keep paper, registry, study and version denominators visible."""
    counts = [
        ('Starting registry', 'Registry records', len(registry)),
        ('Starting registry', 'Source documents', registry['paper_id'].nunique()),
        ('Search inventory', 'Candidate papers', len(papers)),
        ('Search inventory', 'Papers marked recovered', papers['paper_recovered'].eq('Y').sum()),
        ('Search inventory', 'Papers pending retrieval', papers['paper_recovered'].ne('Y').sum()),
        ('Linked evidence', 'Study outcome components', len(components)),
        ('Linked evidence', 'Structural records', components['structure_id'].nunique()),
        ('Linked evidence', 'Named exercises', components['negotiation_scenario'].nunique()),
        ('Linked evidence', 'Contributing paper citations', studies['paper_citation'].nunique()),
        ('Analysis', 'Independent study observations', len(regressions)),
        ('Analysis', 'Exercise groups', regressions['scenario_cluster'].nunique()),
        ('Analysis', 'Study observations with negotiation weights', regressions['negotiations'].gt(0).sum()),
        ('Sensitivity', 'Study-linked version observations', len(structures)),
        ('Sensitivity', 'Strict version observations', structures['strict_eligible'].eq(True).sum()),
    ]
    return pd.DataFrame(counts, columns=['stage', 'unit', 'count'])


def build_data(root, output_dir):
    """Load released inputs, regenerate study files, and export the data flow."""
    root, output_dir = Path(root), Path(output_dir)
    sources = root / 'data' / 'sources'
    inventory = root / 'data' / 'inventory'
    components = pd.read_csv(sources / 'study_outcomes.csv')
    structures = pd.read_csv(sources / 'structure_inputs.csv')
    scores = pd.read_csv(sources / 'structural_scores.csv')
    require(scores['observation_id'].is_unique, 'Duplicate structural score ID')
    require(set(scores['observation_id']) == set(structures['observation_id']),
            'Structural input and score IDs differ')
    structures = structures.merge(scores, on='observation_id', how='left', validate='one_to_one')

    # Where released numerical inputs exist, the companion module can verify
    # and reproduce the measures. Other rows retain their recorded calculations.
    from structure_metrics import apply_metric_inputs
    structures, metric_audit = apply_metric_inputs(structures, sources)

    studies, joined = study_observations(components, structures)
    versions = version_observations(components, structures)
    papers = pd.read_csv(inventory / 'paper_inventory.csv')
    registry = pd.read_csv(inventory / 'starting_study_registry.csv')
    links = pd.read_csv(inventory / 'paper_study_links.csv')
    require(links['study_id'].is_unique, 'Paper crosswalk must contain one record per study')
    require(set(studies['observation_id']) == set(links['study_id']), 'Paper crosswalk and study IDs differ')
    study_inputs = studies.drop(columns=MEASURES).merge(
        links[['study_id', 'paper_id']], left_on='observation_id', right_on='study_id',
        how='left', validate='one_to_one').drop(columns='study_id')
    study_inputs = study_inputs.merge(papers[['paper_id', 'paper_link', 'search_sources']], on='paper_id',
                                      how='left', validate='many_to_one')
    final = studies[REGRESSION_COLUMNS].dropna(subset=['agreement_rate', *MEASURES, *CONTROLS]).copy()
    data_flow = flow_table(papers, registry, studies, components, versions, final)

    output_dir.mkdir(parents=True, exist_ok=True)
    study_inputs.to_csv(output_dir / 'study_inputs.csv', index=False)
    final.to_csv(output_dir / 'regression_data.csv', index=False)
    versions.to_csv(output_dir / 'version_comparison_data.csv', index=False)
    data_flow.to_csv(output_dir / 'data_flow.csv', index=False)
    metric_audit.to_csv(output_dir / 'metric_reproduction.csv', index=False)
    joined[['study_id', 'component_id', 'structure_id', 'within_study_weight']].to_csv(
        output_dir / 'component_weights.csv', index=False)
    return final, versions, data_flow
