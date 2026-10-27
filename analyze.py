"""Summarize campaign response rates without exporting customer records."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

GROUPS = ['contact', 'month', 'poutcome', 'campaign_band']

def prepare(frame):
    required = ['contact', 'month', 'poutcome', 'campaign', 'y']
    if not set(required).issubset(frame.columns):
        raise ValueError('Required columns: ' + ', '.join(required))
    if frame.empty:
        raise ValueError('Input must contain records')
    d = frame[required].copy()
    if d.isna().any().any():
        raise ValueError('Required columns cannot contain missing values')
    if not d.y.isin(['yes', 'no']).all():
        raise ValueError('y must be yes or no')
    c = pd.to_numeric(d.campaign, errors='raise')
    if not (np.isfinite(c) & (c >= 1) & (c % 1 == 0)).all():
        raise ValueError('campaign must contain positive integers')
    d['campaign_band'] = pd.cut(c, [0, 1, 3, 6, np.inf], labels=['1', '2–3', '4–6', '7+'])
    d['subscribed'] = d.y.eq('yes').astype(int)
    return d

def summarize(d, group):
    result = d.groupby(group, observed=True, sort=True).subscribed.agg(records='size', subscriptions='sum').reset_index()
    result['response_rate'] = result.subscriptions / result.records
    return result

def run(frame, output):
    d = prepare(frame)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    tables = []
    for group in GROUPS:
        t = summarize(d, group).rename(columns={group: 'segment'})
        t.insert(0, 'dimension', group)
        tables.append(t)
    combined = pd.concat(tables, ignore_index=True)
    combined.to_csv(out / 'segment_summary.csv', index=False)
    audit = {'records': len(d), 'subscriptions': int(d.subscribed.sum()),
             'response_rate': float(d.subscribed.mean()),
             'unknown_categories': {k: int(d[k].eq('unknown').sum()) for k in GROUPS[:3]}}
    (out / 'summary.json').write_text(json.dumps(audit, indent=2) + '\n')
    chart = summarize(d, 'campaign_band')
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(chart.campaign_band.astype(str), chart.response_rate * 100, color='#147d92')
    ax.set(title='Response by number of campaign contacts', xlabel='Contacts in current campaign', ylabel='Subscription response (%)')
    for i, row in chart.iterrows():
        ax.text(i, row.response_rate * 100 + .3, f'n={row.records:,}', ha='center', fontsize=10)
    ax.set_ylim(0, chart.response_rate.max() * 100 + 3)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / 'contact_response.svg')
    plt.close(fig)
    return audit

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', help='Semicolon-delimited CSV')
    p.add_argument('--output', default='results')
    args = p.parse_args()
    print(json.dumps(run(pd.read_csv(args.input, sep=';'), args.output), indent=2))
