"""Format the manuscript tables and draw the Study 1 figures from results."""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd


LABELS = {
    'agreement_rate': 'Agreement rate',
    'bargaining_zone_share': 'Bargaining-zone size',
    'search_complexity': 'Search complexity',
    'number_of_issues': 'Number of issues',
    'number_of_parties': 'Number of parties',
    'number_of_compatible_issues': 'Compatible issues',
    'automated_counterpart': 'Automated counterpart',
    'non_unanimous_rule': 'Non-unanimous rule',
    'const': 'Intercept',
}
PRIMARY_MODELS = ['bz_controls', 'sc_controls', 'joint']


def number(value, digits=3, leading_zero=False):
    if pd.isna(value):
        return '—'
    text = f'{value:.{digits}f}'
    if text.startswith('-') and float(text) == 0:
        text = text[1:]
    if not leading_zero:
        text = text.removeprefix('0') if text.startswith('0.') else text.replace('-0.', '-.')
    return text.replace('-', '−')


def interval(low, high):
    return f'[{number(low)}, {number(high)}]' if pd.notna(low) and pd.notna(high) else '—'


def p_value(value):
    return '< .001' if pd.notna(value) and value < .001 else number(value)


def table(label, title, columns, rows, note):
    return {'label': label, 'title': title, 'columns': columns, 'rows': rows, 'note': note}


def descriptives_table(tables):
    stats = tables['descriptive_statistics'].query("dataset == 'study'").set_index('variable')
    corr = tables['correlations'].query("dataset == 'study'").set_index(['variable', 'other_variable'])
    variables = list(stats.index)
    rows = []
    for i, name in enumerate(variables):
        values = stats.loc[name]
        cells = [f'{i + 1}. {LABELS[name]}', number(values['mean'], 2, True),
                 number(values['std'], 2, True)]
        cells.extend(number(corr.loc[(other, name), 'r'], 2) for other in variables[:i])
        rows.append(cells + ['—'] + [''] * (len(variables) - i - 1))
    return table('Table 1', 'Descriptive statistics and correlations',
                 ['Variable', 'M', 'SD', *map(str, range(1, len(variables) + 1))], rows,
                 f'Note. N = {int(stats.iloc[0]["count"])} studies. Values are on their original scales. '
                 'The lower triangle reports Pearson correlations. Agreement rate and both structural '
                 'measures are proportions. The last two controls can be fractions when studies combine conditions.')


def regression_table(tables):
    coefficients = tables['coefficients'].query("dataset == 'study' and inference == 'CR1'").set_index(['model', 'term'])
    fits = tables['model_fit'].query("dataset == 'study'").set_index('model')
    rows = []
    for term in ['bargaining_zone_share', 'search_complexity', *list(LABELS)[3:8], 'const']:
        cells = [LABELS[term]]
        for model in PRIMARY_MODELS:
            if (model, term) not in coefficients.index:
                cells.append('—')
                continue
            est = coefficients.loc[(model, term)]
            stars = '***' if est.p < .001 else '**' if est.p < .01 else '*' if est.p < .05 else ''
            cells.append(f'{number(est.b)}{stars}\n({number(est.se)})')
        rows.append(cells)
    for label, key, formatter in [('Studies', 'n', lambda x: str(int(x))),
                                  ('Exercise groups', 'scenario_groups', lambda x: str(int(x))),
                                  ('R²', 'r_squared', number), ('Adjusted R²', 'adjusted_r_squared', number)]:
        rows.append([label, *(formatter(fits.loc[model, key]) for model in PRIMARY_MODELS)])
    return table('Table 2', 'Regression estimates for observed agreement rates',
                 ['Predictor', '(1) Bargaining zone', '(2) Search complexity', '(3) Joint model'], rows,
                 'Note. Entries are coefficients with exercise-clustered standard errors in parentheses. '
                 'Each model includes the five listed controls. Continuous predictors and counts are standardized. '
                 'Agreement rate is a proportion. A dash in parentheses marks uncertainty unavailable for a '
                 'singleton control. * p < .05. ** p < .01. *** p < .001. Exact p values are in the replication output.')


def workflow_table(data_flow):
    rows = [[str(r.stage), str(r.unit), str(int(r.count))] for r in data_flow.itertuples()]
    return table('Table S1', 'From source records to the analysis sample',
                 ['Stage', 'Unit counted', 'Count'], rows,
                 'Note. Registry records, papers, outcome components, structures and independent studies are '
                 'different units. The inventories document retrieval and matching. Code reproduces these counts '
                 'from the released coded records.')


def robustness_table(tables):
    hypotheses = tables['hypothesis_tests'].set_index(['dataset', 'hypothesis'])
    intervals = tables['bootstrap_intervals'].set_index(['dataset', 'resampling', 'test'])
    fits = tables['model_fit'].set_index(['dataset', 'model'])
    coefficients = tables['coefficients'].set_index(['dataset', 'model', 'inference', 'term'])
    rows = []
    for label, dataset in [('Primary study analysis', 'study'),
                           ('Study-linked numerical versions', 'structure'),
                           ('Stricter numerical versions', 'strict_structure')]:
        h1, h2 = hypotheses.loc[(dataset, 'H1')], hypotheses.loc[(dataset, 'H2')]
        rows.append([label, str(int(h1.n)), number(h1.estimate), interval(h1.ci_low, h1.ci_high),
                     number(h2.estimate), interval(h2.ci_low, h2.ci_high)])
    for label, dataset in [('Means by exercise', 'exercise_mean'),
                           ('Strict means by exercise', 'strict_exercise_mean')]:
        fit = fits.loc[(dataset, 'joint')]
        term = coefficients.loc[(dataset, 'joint', 'CR1', 'search_complexity')]
        delta = fits.loc[(dataset, 'sc_controls'), 'r_squared'] - fits.loc[(dataset, 'bz_controls'), 'r_squared']
        rows.append([label, str(int(fit.n)), number(term.b), interval(term.ci_low, term.ci_high),
                     number(delta), '—'])
    h1, h2 = hypotheses.loc[('study', 'H1')], hypotheses.loc[('study', 'H2')]
    for label, key in [('Study-row resampling', 'observation'), ('Exercise-group resampling', 'exercise')]:
        one = intervals.loc[('study', key, 'H1')]
        two = intervals.loc[('study', key, 'H2')]
        rows.append([label, str(int(h1.n)), number(h1.estimate), interval(one.ci_low, one.ci_high),
                     number(h2.estimate), interval(two.ci_low, two.ci_high)])
    weighted = coefficients.loc[('study', 'weighted_joint', 'CR1', 'search_complexity')]
    rows.append(['Study model weighted by encounters', str(int(fits.loc[('study', 'weighted_joint'), 'n'])),
                 number(weighted.b), interval(weighted.ci_low, weighted.ci_high), '—', '—'])
    hc3 = coefficients.loc[('study', 'joint', 'HC3', 'search_complexity')]
    rows.append(['HC3 standard errors', str(int(h1.n)), number(hc3.b),
                 interval(hc3.ci_low, hc3.ci_high), '—', '—'])
    weighted_n = str(int(fits.loc[('study', 'weighted_joint'), 'n']))
    for label, key in [('Weighted study-row resampling', 'observation_weighted'),
                        ('Weighted exercise-group resampling', 'exercise_weighted')]:
        weighted_interval = intervals.loc[('study', key, 'H1')]
        rows.append([label, weighted_n, number(weighted.b),
                     interval(weighted_interval.ci_low, weighted_interval.ci_high), '—', '—'])
    return table('Table S2', 'Sensitivity to observation unit and inference',
                 ['Analysis', 'N', 'SC b', '95% SC interval', 'ΔR²', '95% ΔR² interval'], rows,
                 'Note. SC is search complexity in the joint model. ΔR² subtracts the bargaining-zone model’s '
                 'R² from the search-complexity model’s R². The first five SC intervals use exercise-clustered '
                 'standard errors. Rows named for resampling use percentile intervals. The ΔR² intervals in '
                 'the first three rows resample exercise groups. Weighted analyses use completed negotiation '
                 'encounters. All omission checks and full results for the comparison samples are supplied '
                 'with the replication outputs.')


def figures(studies, tables, output_dir):
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
                         'font.size': 13, 'axes.labelsize': 15, 'xtick.labelsize': 12,
                         'ytick.labelsize': 12, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.7), sharey=True, layout='constrained')
    for ax, name in zip(axes, ['bargaining_zone_share', 'search_complexity']):
        x = studies[name].to_numpy()
        y = studies['agreement_rate'].to_numpy()
        ax.scatter(x, y, color='#444444', alpha=.48, edgecolors='white', linewidth=.3, s=28)
        slope, intercept = np.polyfit(x, y, 1)
        line = np.array([x.min(), x.max()])
        ax.plot(line, intercept + slope * line, color='black', linewidth=1.35)
        ax.set(xlabel=LABELS[name], xlim=(-.025, 1.025), ylim=(-.025, 1.025),
               xticks=[0, .25, .5, .75, 1], yticks=[0, .25, .5, .75, 1])
        ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_ylabel('Observed agreement rate')
    for suffix in ['png', 'svg']:
        fig.savefig(output_dir / f'figure_2_associations.{suffix}', dpi=300)
    plt.close(fig)

    co = tables['coefficients'].query("dataset == 'study' and inference == 'CR1' and term == 'search_complexity'").set_index('model')
    models = ['sc_only', 'sc_controls', 'joint', 'weighted_joint']
    labels = ['Search complexity alone', 'With basic controls', 'Joint model', 'Weighted joint model']
    fig, ax = plt.subplots(figsize=(8.4, 3.0), layout='constrained')
    for i, model in enumerate(models):
        r = co.loc[model]
        ax.errorbar(100 * r.b, i, xerr=[[100 * (r.b-r.ci_low)], [100 * (r.ci_high-r.b)]],
                    fmt='o', color='black', capsize=3, markersize=5)
    ax.set(yticks=list(range(len(models))), yticklabels=labels,
           xlabel='Change in agreement rate (percentage points)')
    ax.axvline(0, color='#888888', linewidth=.9, linestyle='--')
    ax.invert_yaxis()
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(axis='y', length=0)
    for suffix in ['png', 'svg']:
        fig.savefig(output_dir / f'figure_s1_coefficients.{suffix}', dpi=300)
    plt.close(fig)


def build_presentation(studies, tables, data_flow, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    formatted = [descriptives_table(tables), regression_table(tables),
                 workflow_table(data_flow), robustness_table(tables)]
    (output_dir / 'journal_tables.json').write_text(json.dumps(formatted, ensure_ascii=False, indent=2),
                                                   encoding='utf-8')
    for t in formatted:
        filename = t['label'].lower().replace(' ', '_') + '.csv'
        with (output_dir / filename).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(t['columns'])
            writer.writerows(t['rows'])
    figures(studies, tables, output_dir)
    return formatted
