"""Turn the saved calculations into the paper's tables and figures.

No models are estimated here. Every displayed number comes from a CSV produced
by analysis.py. Table definitions are saved as JSON and Markdown so the Word
paper and the notebook use the same numbers.
"""
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


LABELS = {
    'agreement_rate': 'Agreement rate',
    'search_complexity': 'Search complexity',
    'bargaining_zone_share': 'Bargaining-zone size',
    'number_of_issues': 'Number of issues',
    'number_of_parties': 'Number of parties',
    'number_of_compatible_issues': 'Compatible issues',
    'automated_counterpart': 'Automated / AI counterpart',
    'non_unanimous_rule': 'Agreement without unanimity',
}
VARIABLES = list(LABELS)


def number(value, digits=3):
    if pd.isna(value):
        return '—'
    text = f'{float(value):.{digits}f}'
    if float(text) == 0:
        text = text.lstrip('-')
    return text.replace('-0.', '−.').replace('0.', '.', 1) if abs(float(value)) < 1 else text.replace('-', '−')


def p_text(value):
    if pd.isna(value):
        return 'p unavailable'
    return 'p < .001' if value < .001 else f'p = {number(value)}'


def stars(p):
    return '***' if p < .001 else '**' if p < .01 else '*' if p < .05 else ''


def interval(low, high):
    return f'[{number(low)}, {number(high)}]'


def one(frame, **filters):
    rows = frame
    for key, value in filters.items():
        rows = rows.loc[rows[key].eq(value)]
    if len(rows) != 1:
        raise ValueError(f'Expected one display value for {filters}; found {len(rows)}')
    return rows.iloc[0]


def correlation_table(data):
    rows = []
    for index, name in enumerate(VARIABLES):
        values = data[name]
        correlations = []
        for other_index, other in enumerate(VARIABLES):
            if other_index == index:
                correlations.append('—')
            elif other_index > index:
                correlations.append('')
            else:
                r, p = pearsonr(values, data[other])
                correlations.append(number(r, 2) + stars(p))
        rows.append([f'{index+1}. {LABELS[name]}', number(values.mean(),2),
                     number(values.std(ddof=1),2), *correlations])
    return {'label':'Table 1', 'title':'Descriptive statistics and correlations',
            'columns':['Variable','Mean','SD',*[str(index+1) for index in range(len(VARIABLES))]],
            'rows':rows, 'landscape':True,
            'widths':[2.1,.55,.55,*([.55]*len(VARIABLES))],
            'note':f'Note. N = {len(data)} observations. Agreement rate and both structural measures are on 0–1 scales. '
                   'Counts are shown in their original units and can be averages across conditions. The last two controls are proportions when an observation combines different conditions. '
                   'SD = standard deviation. * p < .05. ** p < .01. *** p < .001. Correlations are descriptive.'}


def regression_table(coefficients, fits, dataset, label, title):
    coefficient_rows = coefficients.loc[coefficients.dataset.eq(dataset)]
    rows = []
    for term in VARIABLES[1:]:
        cells = [LABELS[term]]
        for model in ['M1','M2','M3','M4','M5']:
            selected = coefficient_rows.loc[coefficient_rows.model.eq(model) & coefficient_rows.term.eq(term)]
            if selected.empty:
                cells.append('—')
            else:
                item = selected.iloc[0]
                if pd.isna(item.se):
                    cells.append(number(item.b)+'\nSE unavailable')
                else:
                    cells.append(number(item.b)+stars(item.p)+f'\n({number(item.se)})\n'+p_text(item.p))
        rows.append(cells)
    for name, field, count in [('Observations','n',True),('R²','r_squared',False),
                               ('Adjusted R²','adjusted_r_squared',False)]:
        rows.append([name,*[str(int(one(fits,dataset=dataset,model=model)[field])) if count else
                            number(one(fits,dataset=dataset,model=model)[field])
                            for model in ['M1','M2','M3','M4','M5']]])
    selected_fits = fits.loc[fits.dataset.eq(dataset) & fits.model.isin(['M1','M2','M3','M4','M5'])]
    unavailable = selected_fits.controls_with_unavailable_uncertainty.fillna('').str.len().gt(0).any()
    omitted = selected_fits.dropped_controls.fillna('').str.contains('automated_counterpart').any()
    note = ('Note. The dependent variable is agreement rate (0–1). Entries are coefficients, with HC3 robust standard errors '
            'in parentheses and two-sided p values beneath. Continuous predictors and the three count controls are standardized; '
            'indicator controls retain their original scales. Every model includes a constant. '
            '— indicates that a predictor is not included or is constant in this sample. '
            '* p < .05. ** p < .01. *** p < .001.')
    if unavailable:
        note += (' Only one observation involves an automated counterpart. Its indicator coefficient can be fitted, '
                 'but its own HC3 standard error is unavailable. The other coefficients have estimable HC3 standard errors.')
    if omitted:
        note += ' The automated-counterpart control is constant at zero and is omitted.'
    return {'label':label,'title':title,
            'columns':['Predictor','(1)\nSearch complexity','(2)\n+ controls','(3)\nBoth + controls',
                       '(4)\nBargaining zone','(5)\n+ controls'],
            'rows':rows,'landscape':False,'note':note,
            'widths':[1.8,.94,.94,.94,.94,.94]}


def robustness_table(coefficients, fits, boots, omissions, hypotheses):
    rows = []
    for dataset, label in [('main','Main'),('strict','Strict')]:
        joint = one(coefficients,dataset=dataset,model='M3',term='search_complexity')
        delta = one(hypotheses,dataset=dataset,hypothesis='H2')
        if dataset == 'strict':
            rows.append(['Strict inclusion',label,str(int(joint.n)),number(joint.b),p_text(joint.p),
                         number(one(fits,dataset=dataset,model='M3').r_squared),
                         number(delta.estimate)+'\n'+interval(delta.ci_low,delta.ci_high)])
    for dataset, label in [('main','Main'),('strict','Strict')]:
        for test_name in ['H1']:
            item = one(boots,dataset=dataset,test=test_name)
            if test_name == 'H1':
                delta = one(boots,dataset=dataset,test='H2')
                rows.append(['5,000 observation resamples',label,str(int(item.n)),
                             interval(item.ci_low,item.ci_high),'—','—',interval(delta.ci_low,delta.ci_high)])
            else:
                rows.append(['Resampled comparison without controls',label,str(int(item.n)),
                             '—','—','—',interval(item.ci_low,item.ci_high)])
    for weighted in [False,True]:
        if weighted:
            for dataset, label in [('main','Main'),('strict','Strict')]:
                item = one(coefficients,dataset=dataset,model='weighted_joint',term='search_complexity')
                rows.append(['Negotiation-count weights (Model 6)',label,str(int(item.n)),number(item.b),
                             p_text(item.p),number(one(fits,dataset=dataset,model='weighted_joint').r_squared),'—'])
                boot = one(boots,dataset=dataset,test='weighted_search_complexity')
                rows.append(['Weighted observation resamples',label,str(int(item.n)),
                             interval(boot.ci_low,boot.ci_high),'—','—','—'])
        for dataset, label in [('main','Main'),('strict','Strict')]:
            selected = omissions.loc[omissions.dataset.eq(dataset) & omissions.weighted.eq(weighted)]
            if selected.error.fillna('').str.len().gt(0).any():
                raise ValueError('An omission failed and needs a display decision')
            if not len(selected):
                raise ValueError('Omission results missing')
            passed = selected.negative_and_significant.astype(str).str.lower().isin(['true','y','1']).sum()
            delta_range = '—' if weighted else interval(selected.r_squared_difference.min(),selected.r_squared_difference.max())
            rows.append(['Weighted omissions' if weighted else 'Single-observation omissions',
                         label,str(len(selected)),interval(selected.search_complexity_b.min(),selected.search_complexity_b.max()),
                         f'{passed}/{len(selected)} p < .05','—',delta_range])
    for dataset,label in [('aggregate_main','Combined payoffs'),('aggregate_strict','Strict combined payoffs')]:
        item = one(coefficients,dataset=dataset,model='M3',term='search_complexity')
        delta = one(fits,dataset=dataset,model='M2').r_squared-one(fits,dataset=dataset,model='M5').r_squared
        rows.append(['Mean outcome for identical payoffs',label,str(int(item.n)),number(item.b),p_text(item.p),
                     number(one(fits,dataset=dataset,model='M3').r_squared),number(delta)])
    return {'label':'Table 3','title':'Confirmation and supplementary checks of the agreement-rate results',
            'columns':['Check','Data','N','Search-complexity coefficient or 95% interval','p value or omission count',
                       'R²','R² difference or 95% interval'],
            'rows':rows,'landscape':True,'widths':[2.35,1.0,.4,1.65,1.2,.6,1.5],
            'note':('Note. Main resampling and omission checks are required for confirmation. Intervals use 5,000 observation draws. '
                    'Omission rows show ranges; their N counts checks and their p column counts negative coefficients with p < .05. '
                    'Other N values are observations. R² difference is Model 2 minus Model 5. Model 6 uses negotiation-count weights.')}


def original_table(outputs):
    frame=pd.read_csv(outputs/'original_main_hypotheses.csv')
    names={'H1':'Bargaining-zone size (+)','H2':'Search complexity (−)',
           'H3':'Explained-variation comparison','H4':'Search complexity with both predictors (−)'}
    rows=[]
    for item in frame.itertuples(index=False):
        rows.append([item.hypothesis+': '+names[item.hypothesis],item.model,
                     number(item.primary_estimate),'—' if pd.isna(item.primary_p) else p_text(item.primary_p),
                     interval(item.bootstrap_ci_low,item.bootstrap_ci_high),
                     f'{item.omissions_passed}/{item.omissions_required}',
                     'Yes' if item.full_confirmation_met else 'No'])
    return {'label':'Table C4','title':'Main hypothesis tests specified in the original registration',
            'columns':['Original hypothesis','Model','Estimate','p value','95% resampling interval','Omissions passing','Full criteria met'],
            'rows':rows,'landscape':True,'widths':[2.7,1,.7,.9,1.5,1,1],
            'note':('Note. N = 103 payoff records using the corrected research evidence. Coefficient rows report b for a standardized predictor; '
                    'H3 reports R²(Model 2) − R²(Model 5). Each interval uses 5,000 individual-payoff-row draws. '
                    'The original criteria require the full-sample test, an interval entirely in the predicted direction, '
                    'and the required direction and significance after every single-row omission. H3 requires a positive '
                    'difference after each omission. The five regressions appear in Table C2. These original hypothesis '
                    'numbers are separate from H1 and H2 in the main text.')}


def save_markdown(tables, path):
    text=[]
    for entry in tables:
        text += [f'## {entry["label"]}. {entry["title"]}', '',
                 '| '+' | '.join(cell.replace('\n','<br>') for cell in entry['columns'])+' |',
                 '| '+' | '.join(['---']*len(entry['columns']))+' |']
        text += ['| '+' | '.join(str(cell).replace('\n','<br>') for cell in row)+' |' for row in entry['rows']]
        text += ['',entry['note'],'']
    path.write_text('\n'.join(text),encoding='utf-8')


def make_figures(root, outputs):
    data=pd.read_csv(outputs/'regression_data.csv')
    figures=outputs/'figures'; figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.labelsize':14,
                         'xtick.labelsize':11,'ytick.labelsize':11,'axes.titlesize':13.5,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
    fig,axes=plt.subplots(2,1,figsize=(7.2,9),sharey=True)
    for axis,predictor,title in zip(axes,['bargaining_zone_share','search_complexity'],
                                    ['A. Bargaining-zone size','B. Search complexity']):
        axis.scatter(data[predictor],data.agreement_rate,s=32,facecolors='none',edgecolors='black',alpha=.7,linewidth=.8)
        # The line summarizes the corresponding bivariate regression only.
        slope,intercept=np.polyfit(data[predictor],data.agreement_rate,1)
        x=np.linspace(data[predictor].min(),data[predictor].max(),200)
        axis.plot(x,intercept+slope*x,color='black',linewidth=1.4)
        axis.set(title=title,xlabel=LABELS[predictor],ylabel='Agreement rate',xlim=(-.025,1.025),ylim=(-.025,1.05))
        axis.xaxis.set_major_formatter(PercentFormatter(1))
        axis.yaxis.set_major_formatter(PercentFormatter(1))
        axis.set_xticks([0,.25,.5,.75,1]);axis.set_yticks([0,.25,.5,.75,1])
        axis.grid(False)
    fig.tight_layout(h_pad=2)
    fig.savefig(figures/'agreement_relationships.png',dpi=240,bbox_inches='tight');plt.close(fig)
    frequencies=root/'data/inventory/source_frequencies.csv'
    if frequencies.exists():
        source=pd.read_csv(frequencies)
        # The evidence inventory supplies these headers; reject a silent guess.
        label_col='source' if 'source' in source else 'Source'
        n_col='observations' if 'observations' in source else 'analysis_observations'
        if n_col not in source:
            n_col='Observations'
        fig,axis=plt.subplots(figsize=(8,4.5))
        bars=axis.barh(source[label_col],source[n_col],color='0.25',height=.6)
        axis.bar_label(bars,padding=6,fontsize=16)
        axis.invert_yaxis();axis.set_xlabel('Observations identified')
        axis.set_xlim(0,max(source[n_col])*1.18);axis.set_title('Sources used to identify the observations',pad=18)
        axis.spines['left'].set_visible(False);axis.tick_params(axis='y',length=0)
        axis.grid(False);fig.tight_layout()
        fig.savefig(figures/'observation_sources.png',dpi=220,bbox_inches='tight');plt.close(fig)
    return [{'label':'Figure 2','title':'Observed agreement rates and negotiation structure',
             'path':str(figures/'agreement_relationships.png'),
             'note':f'Note. Each point is one observation (N = {len(data)}). Lines summarize the associations before adding controls. Overlapping points may represent several observations.'}]


def build_flow(root, outputs):
    """Count each source with its own unit, without subtracting unlike totals."""
    inventory = root/'data/inventory'
    if not (inventory/'paper_inventory.csv').exists():
        return
    papers = pd.read_csv(inventory/'paper_inventory.csv')
    registry = pd.read_csv(inventory/'starting_study_registry.csv')
    paper_links = pd.read_csv(inventory/'observation_papers.csv')
    main = pd.read_csv(outputs/'regression_data.csv')
    strict = pd.read_csv(outputs/'strict_regression_data.csv')
    components = pd.read_csv(outputs/'component_evidence.csv')
    eligibility = pd.read_csv(outputs/'observation_eligibility.csv')
    full = papers.retrieval_status.isin(['Yes','Chapter version'])
    contributing = papers.paper_id.isin(paper_links.paper_id)
    if len(paper_links) != len(main) or not paper_links.observation_id.is_unique:
        raise ValueError('Each observation needs one paper link')
    if int(papers.observations_contributed.sum()) != len(main):
        raise ValueError('Paper contributions do not match the observation count')
    records = [
        ('Starting review records',len(registry),'Review records','data/inventory/starting_study_registry.csv'),
        ('Papers in the starting review records',registry.paper_id.nunique(),'Papers','data/inventory/starting_study_registry.csv'),
        ('Papers in the combined search',len(papers),'Papers','data/Paper_inventory.xlsx'),
        ('Verified full texts or complete chapters',int(full.sum()),'Papers','data/Paper_inventory.xlsx'),
        ('No locally verified full text',int((~full).sum()),'Papers','data/Paper_inventory.xlsx'),
        ('Papers contributing observations',int(contributing.sum()),'Papers','data/inventory/observation_papers.csv'),
        ('Contributing papers with verified full texts',int((contributing&full).sum()),'Papers','data/Paper_inventory.xlsx'),
        ('Contributing papers supported by other evidence',int((contributing&~full).sum()),'Papers','data/Paper_inventory.xlsx'),
        ('Underlying agreement results',len(components),'Source-result records','data/Observation_data.xlsx'),
        ('Main analysis',len(main),'Observations','data/regression_data.csv'),
        ('Payoff information linked to the observations',components.payoff_id.nunique(),'Payoff records','data/raw_payoff_catalog.json'),
        ('Named negotiation exercises',components.negotiation_exercise.nunique(),'Exercise names','data/inventory/exercise_inventory.csv'),
        ('Strict analysis',len(strict),'Observations','outputs/strict_regression_data.csv'),
        ('Strict observations using a subset of conditions',int(eligibility.strict_coverage.eq('Recoverable subset of conditions').sum()),'Observations','outputs/observation_eligibility.csv'),
        ('Combined-payoff comparison',len(pd.read_csv(outputs/'aggregate_main.csv')),'Combined payoff records','outputs/aggregate_main.csv'),
        ('Strict combined-payoff comparison',len(pd.read_csv(outputs/'aggregate_strict.csv')),'Combined payoff records','outputs/aggregate_strict.csv')]
    pd.DataFrame(records,columns=['Stage','Count','Unit','File']).to_csv(outputs/'data_flow.csv',index=False)
    sources = sorted({item.strip() for value in papers.discovery_sources.dropna()
                      for item in str(value).split('|') if item.strip()})
    counts=[]
    for source in sources:
        selected = papers.discovery_sources.fillna('').str.split('|').map(lambda values: source in [value.strip() for value in values])
        ids=set(papers.loc[selected,'paper_id'])
        counts.append({'Source':source,'Papers':int(selected.sum()),
                       'Full texts or complete chapter versions':int((selected&full).sum()),
                       'Papers contributing observations':int((selected&contributing).sum()),
                       'Observations':int(paper_links.paper_id.isin(ids).sum())})
    pd.DataFrame(counts).to_csv(outputs/'source_frequencies.csv',index=False)
    return records


def build_tables(root, outputs):
    root,outputs=Path(root),Path(outputs)
    coeff=pd.read_csv(outputs/'coefficients.csv');fits=pd.read_csv(outputs/'model_fit.csv')
    boots=pd.read_csv(outputs/'bootstrap_intervals.csv');omit=pd.read_csv(outputs/'leave_one_out.csv')
    hyp=pd.read_csv(outputs/'hypothesis_tests.csv')
    tables=[correlation_table(pd.read_csv(outputs/'regression_data.csv')),
            regression_table(coeff,fits,'main','Table 2','Agreement rates predicted by search complexity and bargaining-zone size'),
            robustness_table(coeff,fits,boots,omit,hyp),
            regression_table(coeff,fits,'strict','Table C1','Agreement rates with strict inclusion'),
            regression_table(coeff,fits,'aggregate_main','Table C2','Agreement rates after combining identical payoff tables and reservation values'),
            regression_table(coeff,fits,'aggregate_strict','Table C3','Strict observations after combining identical payoff tables and reservation values')]
    if (outputs/'original_main_hypotheses.csv').exists():
        tables.append(original_table(outputs))
    (outputs/'tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2),encoding='utf-8')
    save_markdown(tables,outputs/'tables.md')
    for entry in tables:
        pd.DataFrame(entry['rows'],columns=entry['columns']).to_csv(outputs/(entry['label'].lower().replace(' ','_')+'.csv'),index=False)
    figures=make_figures(root,outputs)
    build_flow(root,outputs)
    return tables,figures


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    build_tables(root,root/'outputs')
