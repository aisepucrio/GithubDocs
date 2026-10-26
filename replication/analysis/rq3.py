"""Adapted from the supplied analysis notebook; see docs/methodology.md."""
from pathlib import Path
import os
import matplotlib
matplotlib.use('Agg')
display = print

# Original notebook cell 3
# 0.2 — imports, palette, plotting defaults  (same design system as the RQ1/RQ2 notebook)
import os, re, glob, json, itertools, textwrap
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

try:                                   # notebook -> rich tables; plain python -> print
    from IPython.display import display
except ImportError:
    display = print

FIGDIR = 'figs_rq3'
os.makedirs(FIGDIR, exist_ok=True)

# --- palette -------------------------------------------------------------
# The five DOME model slots are carried over UNCHANGED from the RQ1/RQ2 notebook, so a
# model keeps its hue across every figure of the paper. Claude Code is a sixth entity, not a
# sixth model: it gets its own slot, validated with the other five on the adjacent pairlist
# (worst adjacent CVD dE 9.2 deutan / 23.0 tritan, worst normal-vision dE 27.6, contrast 4.9:1).
SURFACE   = '#fcfcfb'
INK       = '#0b0b0b'
INK_2     = '#52514e'
MUTED     = '#898781'
GRID      = '#e1e0d9'
AXIS      = '#c3c2b7'

CC        = 'Claude Code (Opus 5)'                       # the entity under comparison
GD_MODELS = ['Gemini 3.1 Flash-Lite', 'Llama 3.1 8B', 'Mistral-Nemo 12B',
             'Qwen2.5-Coder 14B', 'GPT-5.6 Luna']
MODEL_ORDER = GD_MODELS + [CC]
MODEL_COLOR = dict(zip(MODEL_ORDER, ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#eda100',
                                     '#c2185b']))
NM, NG = len(MODEL_ORDER), len(GD_MODELS)
MODEL_SHORT = {'Gemini 3.1 Flash-Lite': 'Gemini\n3.1 FL', 'Llama 3.1 8B': 'Llama\n3.1 8B',
               'Mistral-Nemo 12B': 'Mistral\nNemo 12B', 'Qwen2.5-Coder 14B': 'Qwen2.5\nCoder 14B',
               'GPT-5.6 Luna': 'GPT-5.6\nLuna', CC: 'Claude Code\nOpus 5'}
MODEL_TICKS = [MODEL_SHORT[m] for m in MODEL_ORDER]
GD_TICKS    = [MODEL_SHORT[m] for m in GD_MODELS]

# system-level encoding, used where the figure contrasts the two SYSTEMS rather than the models
SYS_COLOR = {'DOME': '#2a78d6', 'Claude Code': '#c2185b'}
TIE_COLOR = GRID

# Diverging ramp for the 1-5 Likert scale (blue<->red, neutral gray midpoint).
LIKERT_COLOR = {1: '#b03434', 2: '#e88a86', 3: '#c3c2b7', 4: '#86b6ef', 5: '#1c5cab'}
LIKERT_INK   = {1: 'white',   2: INK,       3: INK,       4: INK,       5: 'white'}

CAT8 = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
SEQ = mpl.colors.LinearSegmentedColormap.from_list(
    'ghd_blue', ['#cde2fb', '#9ec5f4', '#5598e7', '#2a78d6', '#256abf', '#184f95', '#0d366b'])
ST_CRITICAL, ST_GOOD = '#d03b3b', '#0ca30c'      # reserved: never a series color

mpl.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.edgecolor': AXIS, 'axes.linewidth': 0.8, 'axes.labelcolor': INK_2,
    'axes.titlesize': 12, 'axes.titleweight': 'bold', 'axes.titlecolor': INK,
    'axes.titlelocation': 'left', 'axes.titlepad': 24,
    'axes.spines.top': False, 'axes.spines.right': False,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK_2, 'ytick.labelcolor': INK_2,
    'grid.color': GRID, 'grid.linewidth': 0.8, 'legend.frameon': False,
    'lines.linewidth': 2, 'lines.markersize': 8,
})

def head(fig, title, sub=None):
    H = fig.get_figheight()
    fig.suptitle(title, x=.02, ha='left', va='top', y=1 - .12 / H, fontweight='bold', fontsize=12)
    if sub:
        fig.text(.02, 1 - .40 / H, sub, color=MUTED, fontsize=8.5, va='top')
    fig._head = (.66 if sub else .44) / H

def save(fig, name):
    fig.tight_layout(rect=[0, 0, 1, 1 - getattr(fig, '_head', 0)])
    for ext in ('png', 'pdf'):
        fig.savefig(f'{FIGDIR}/{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  -> {FIGDIR}/{name}.png | .pdf')

def ink_on(color):
    r, g, b = mpl.colors.to_rgb(color)
    return INK if (0.2126 * r + 0.7152 * g + 0.0722 * b) > 0.5 else 'white'

def ygrid(ax):
    ax.set_axisbelow(True); ax.grid(axis='y', which='major'); ax.grid(axis='x', visible=False)

def xgrid(ax):
    ax.set_axisbelow(True); ax.grid(axis='x', which='major'); ax.grid(axis='y', visible=False)

print('setup ok')

# Original notebook cell 4
DATA_DIR = os.environ['DOME_DATA_DIR']
GD_PATHS = sorted(glob.glob(os.path.join(DATA_DIR, '*_answers_merged.csv.gz')))
CC_PATH = os.path.join(DATA_DIR, 'claude_code_answers.csv.gz')


# Original notebook cell 5
# 0.4 — load both exports and normalise them onto ONE schema
DIMS = {'Concisão': 'Conciseness', 'Corretude': 'Correctness',
        'Completude': 'Completeness', 'Clareza': 'Clarity'}
DIM_EN = list(DIMS.values())

MODEL_LABEL = {'gemini-3.1-flash-lite': 'Gemini 3.1 Flash-Lite', 'llama3.1:8b': 'Llama 3.1 8B',
               'mistral-nemo:12b': 'Mistral-Nemo 12B', 'qwen2.5-coder:14b': 'Qwen2.5-Coder 14B',
               'gpt-5.6-luna': 'GPT-5.6 Luna'}
# the two exports spell the test type differently; both land on the same three tasks
TASK_LABEL = {'readme/readme': 'README (generation)', 'readme': 'README (generation)',
              'readme-update/readme_update': 'README (update)', 'readme_update': 'README (update)',
              'changelog/changelog': 'CHANGELOG', 'changelog': 'CHANGELOG'}
TASK_RQ    = {'README (generation)': 'RQ1', 'README (update)': 'RQ1', 'CHANGELOG': 'RQ2'}
TASK_ORDER = ['README (generation)', 'README (update)', 'CHANGELOG']
TASK_SHORT = {'README (generation)': 'README gen', 'README (update)': 'README upd', 'CHANGELOG': 'CHANGELOG'}
# the Claude Code export names the repositories by checkout path; map them onto the DOME keys
REPO_FROM_PATH = {'external_repos/project-a': 'project-a', 'external_repos/project-d': 'project-d',
                  'external_repos/project-c': 'project-c', 'external_repos/project-e': 'project-e',
                  'external_repos/project-f': 'project-f', 'external_repos/project-b': 'project-b'}
REPO_LABEL = {'project-a': 'project-a', 'project-d': 'project-d', 'project-e': 'project-e',
              'project-f': 'project-f', 'project-b': 'project-b', 'project-c': 'project-c'}
REPO_ORDER = list(REPO_LABEL)

# total_tokens == input + output + cache_read + cache_write in BOTH exports (checked below),
# so the token figures can stack the parts without a residual.
TOKCOLS = ['input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens']
NUMCOLS = TOKCOLS + ['total_tokens', 'total_cost', 'num_observations', 'latency_seconds']

def txt(df, col):
    # "Valor Nulo" is this export's null literal; make every text column a clean str
    if col not in df:
        return pd.Series([''] * len(df), index=df.index)
    s = df[col].astype('object').where(df[col].notna(), '').astype(str).str.strip()
    return s.replace('Valor Nulo', '')

def normalise(raw, system, model, repo, tool_calling):
    out = txt(raw, 'C : output')
    err = txt(raw, 'C : metadata_error_message')
    filler = raw['is_filler'].astype(bool) if 'is_filler' in raw else pd.Series(False, index=raw.index)
    d = pd.DataFrame({
        'system': system, 'model': model, 'repo': repo,
        'context_id': raw['context_id'], 'user_id': raw['user_id'],
        'task': raw['C : metadata_test_type'].map(TASK_LABEL),
        'case': pd.to_numeric(raw['C : metadata_config_index'], errors='coerce'),   # the pairing key
        'tool_calling': tool_calling,
        'failed': filler | out.eq('') | err.ne(''),        # empty output or a recorded error
        'out_chars': pd.to_numeric(raw['C : output_char_count']).where(out.ne('')),
    })
    for c in NUMCOLS:
        d[c] = pd.to_numeric(raw.get('C : ' + c), errors='coerce')
    for pt, en in DIMS.items():
        d[en] = pd.to_numeric(raw['Q : ' + pt], errors='coerce')
        d['cmt_' + en] = txt(raw, 'Q : Justifique sua classificação de ' + pt).replace('', np.nan)
    return d

frames = []
for p in GD_PATHS:                                   # --- DOME
    r = pd.read_csv(p, low_memory=False)
    frames.append(normalise(r, 'DOME',
                            r['C : metadata_model_name'].map(MODEL_LABEL),
                            os.path.basename(p).replace('_answers_merged.csv.gz', ''),
                            r['C : is_tool_calling'].astype(str).str.lower().eq('true')))
r = pd.read_csv(CC_PATH, low_memory=False)           # --- Claude Code
frames.append(normalise(r, 'Claude Code', CC,
                        r['C : metadata_repo_path'].map(REPO_FROM_PATH),
                        True))                       # Claude Code only runs agentically

ann = pd.concat(frames, ignore_index=True)           # one row per (context, annotator)
ann['rq'] = ann['task'].map(TASK_RQ)
ann['uid'] = ann['system'] + '#' + ann['repo'] + '#' + ann['context_id'].astype(str)
ann['Overall'] = ann[DIM_EN].mean(axis=1)

# context-level table: the two annotators averaged; this is the unit of analysis
meta = ['system', 'model', 'repo', 'task', 'rq', 'case', 'tool_calling', 'failed', 'out_chars'] + NUMCOLS
ctx = (ann.groupby('uid', as_index=False)
          .agg({**{c: 'first' for c in meta},
                **{d: 'mean' for d in DIM_EN + ['Overall']},
                'user_id': 'nunique'})
          .rename(columns={'user_id': 'n_raters'}))

# Two quality measures, used deliberately and never mixed up:
#   Overall   — CONDITIONAL quality, valid runs only (what the system does when it answers)
#   eff       — EFFECTIVE quality, a failed run scored 1 on every criterion (what a user gets)
for t in (ann, ctx):
    t['eff'] = t['Overall'].where(~t['failed'], 1.0)
    t['model'] = pd.Categorical(t['model'], MODEL_ORDER, ordered=True)

ctxv, annv = ctx[~ctx.failed].copy(), ann[~ann.failed].copy()

# the four parts sum to total_tokens; one Claude Code trace is off by 12 of 424k (Langfuse rounding)
resid = ((ctx[TOKCOLS].sum(axis=1) - ctx['total_tokens']).abs() / ctx['total_tokens']).max()
assert resid < 1e-3, f'token parts != total (worst residual {resid:.2%})'
print(f'{len(ann)} annotations | {len(ctx)} contexts | {ctx.failed.sum()} failed ({ctx.failed.mean():.1%})')
print(f'paired cases: {ctx[ctx.system == "Claude Code"].case.nunique()} covered by both systems')
display(ctx.groupby(['system', 'model'], observed=True)
           .agg(contexts=('uid', 'size'), cases=('case', 'nunique'),
                failed=('failed', 'sum'), fail_pct=('failed', lambda s: round(100 * s.mean(), 1))))

# Original notebook cell 6
# 0.5 — shared helpers
def ci95(s):
    # half-width of the 95% CI of the mean; 0 when n<2
    s = pd.Series(s).dropna()
    return 0.0 if len(s) < 2 else stats.t.ppf(0.975, len(s) - 1) * s.sem()

def pstar(p):
    return 'n/a' if pd.isna(p) else ('p < 0.001' if p < .001 else f'p = {p:.3f}')

def barlabels(ax, bars, fmt='{:.2f}', dy=0.02, size=8, errs=None):
    # value labels double as the relief required by the sub-3:1 contrast of some slots;
    # `errs` lifts each label clear of its own error bar instead of printing on top of it
    errs = [0] * len(bars) if errs is None else list(errs)
    for b, e in zip(bars, errs):
        h = b.get_height()
        if np.isfinite(h):
            ax.text(b.get_x() + b.get_width() / 2, h + (e if np.isfinite(e) else 0) + dy,
                    fmt.format(h), ha='center', va='bottom', fontsize=size, color=INK_2)

# ---- the paired core of RQ3 -------------------------------------------------
# One row per test case per DOME model: Claude Code's score on that case next to the
# model's score on the SAME case. `mode` selects which DOME runs are averaged in.
CC_CASE = ctx[ctx.system == 'Claude Code'].set_index('case')

def paired(metric='eff', mode='both', model=None):
    gd = ctx[ctx.system == 'DOME']
    if mode == 'direct':
        gd = gd[~gd.tool_calling]
    elif mode == 'tool':
        gd = gd[gd.tool_calling]
    if model is not None:
        gd = gd[gd.model == model]
    g = gd.groupby(['model', 'case'], observed=True)[metric].mean().rename('gd')
    j = g.reset_index().join(CC_CASE[metric].rename('cc'), on='case').dropna(subset=['gd', 'cc'])
    j['delta'] = j['cc'] - j['gd']            # > 0  => Claude Code better on that case
    return j

def wilcoxon(j):
    # paired, non-parametric; ties dropped by the default zero_method
    if len(j) < 3 or (j['delta'] == 0).all():
        return np.nan
    return stats.wilcoxon(j['cc'], j['gd']).pvalue

def cliffs_delta(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    gt = (a[:, None] > b[None, :]).sum(); lt = (a[:, None] < b[None, :]).sum()
    return (gt - lt) / (len(a) * len(b))

print('helpers ok')

# Original notebook cell 8
# Figure R3-1 — the headline: effective quality per system, per task.
# Solid = conditional (valid runs only), hatched = effective (failures scored 1).
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), sharey=True)
for ax, t in zip(axes, TASK_ORDER):
    d, dv = ctx[ctx.task == t], ctxv[ctxv.task == t]
    x, w = np.arange(NM), .38
    for k, (src, col, alpha, hatch) in enumerate([(dv, 'Overall', 1.0, None), (d, 'eff', .42, '//')]):
        sub = [src[src.model == m][col] for m in MODEL_ORDER]
        errs = [ci95(s) for s in sub]
        b = ax.bar(x + (k - .5) * w, [s.mean() for s in sub], w * .9, yerr=errs,
                   capsize=2, color=[MODEL_COLOR[m] for m in MODEL_ORDER], alpha=alpha,
                   hatch=hatch, edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
        barlabels(ax, b, dy=.08, size=7.5, errs=errs)
    ax.axhline(3, color=AXIS, lw=1, ls='--', zorder=0)
    ax.axvline(NG - .5, color=AXIS, lw=1.2, zorder=0)          # DOME | Claude Code divider
    ax.set_xticks(x, MODEL_TICKS, fontsize=7.5)
    ax.set_ylim(1, 5.6); ax.set_yticks(range(1, 6)); ygrid(ax)
    ax.set_title(TASK_SHORT[t] + f'  (n = {d.case.nunique()} cases)', fontsize=10.5)
axes[0].set_ylabel('Quality (1–5)')
fig.legend(handles=[Patch(facecolor=MUTED, label='conditional (valid runs only)'),
                    Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE,
                          label='effective (failed run = 1)')],
           ncol=2, loc='lower center', bbox_to_anchor=(.5, -.07))
head(fig, 'RQ3 — DOME models vs. Claude Code, per task',
     'bars are 95% CI · dashed line = neutral (3) · the five leftmost slots are DOME, the rightmost is Claude Code')
save(fig, 'figR3_01_quality_by_task')

# Original notebook cell 9
# Figure R3-2 — where the difference sits: mean rating per criterion.
fig, ax = plt.subplots(figsize=(11.5, 4.6))
w, x = 0.82 / NM, np.arange(len(DIM_EN))
for i, m in enumerate(MODEL_ORDER):
    g = ctx[ctx.model == m]
    s = [g[dim].where(~g.failed, 1) for dim in DIM_EN]          # effective quality per criterion
    errs = [ci95(v) for v in s]
    b = ax.bar(x + (i - (NM - 1) / 2) * w, [v.mean() for v in s], w * .86,
               yerr=errs, capsize=2, color=MODEL_COLOR[m],
               edgecolor=SURFACE, linewidth=1.5, error_kw=dict(ecolor=INK_2, lw=1), label=m)
    barlabels(ax, b, dy=.05, size=6.8, errs=errs)
ax.set_xticks(x, DIM_EN); ax.set_ylim(1, 5.3); ax.set_yticks(range(1, 6))
ax.set_ylabel('Effective quality (1–5)'); ygrid(ax)
ax.axhline(3, color=AXIS, lw=1, ls='--', zorder=0)
ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(.5, -.10), fontsize=8.5)
ax.set_title('RQ3 — quality by criterion')
ax.text(0, 1.02, f'all {ctx.case.nunique()} cases pooled · failed runs scored 1 · bars are 95% CI '
                 '· dashed line = neutral (3)',
        transform=ax.transAxes, color=MUTED, fontsize=8.5)
save(fig, 'figR3_02_quality_by_criterion')

# Original notebook cell 10
# Figure R3-3 — the paired test. Per case, Claude Code minus the DOME model, split by the
# DOME execution mode. Claude Code is agentic, so `tool calling` is the like-for-like column.
MODES = [('direct', 'DOME · direct prompt', 1.0, None),
         ('tool', 'DOME · tool calling', .42, '//')]
fig, ax = plt.subplots(figsize=(9.6, 4.8))
x, w = np.arange(NG), .38
rows = []
for k, (mode, lbl, alpha, hatch) in enumerate(MODES):
    j = paired('eff', mode)
    means = [j[j.model == m]['delta'].mean() for m in GD_MODELS]
    errs = [ci95(j[j.model == m]['delta']) for m in GD_MODELS]
    ax.bar(x + (k - .5) * w, means, w * .9, yerr=errs, capsize=3,
           color=[MODEL_COLOR[m] for m in GD_MODELS], alpha=alpha, hatch=hatch,
           edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
    for xi, m, v, e in zip(x + (k - .5) * w, GD_MODELS, means, errs):
        jj = j[j.model == m]
        p = wilcoxon(jj)
        rows.append(dict(mode=mode, model=m, n=len(jj), delta=round(v, 2),
                         cliffs=round(cliffs_delta(jj['cc'], jj['gd']), 2), p=p))
        top = (v + e + .10) if v >= 0 else (v - e - .10)
        ax.text(xi, top, f'{v:+.2f}\n{pstar(p)}', ha='center',
                va='bottom' if v >= 0 else 'top', fontsize=7.5, color=INK_2, linespacing=1.35)
ax.axhline(0, color=INK, lw=1.2)
ax.set_xticks(x, GD_TICKS, fontsize=8.5); ax.set_ylim(-1.25, 3.35); ygrid(ax)
ax.set_ylabel('Effective quality:  Claude Code − DOME')
ax.text(.995, .97, 'Claude Code better', transform=ax.transAxes, ha='right', va='top',
        fontsize=9, color=SYS_COLOR['Claude Code'], fontweight='bold')
ax.text(.995, .03, 'DOME better', transform=ax.transAxes, ha='right', va='bottom',
        fontsize=9, color=SYS_COLOR['DOME'], fontweight='bold')
ax.legend(handles=[Patch(facecolor=MUTED, label=MODES[0][1]),
                   Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label=MODES[1][1])],
          ncol=2, loc='upper center', bbox_to_anchor=(.5, -.13))
ax.set_title('RQ3 — paired difference on the 54 matched test cases')
ax.text(0, 1.02, 'bars are 95% CI · p is the Wilcoxon signed-rank test on the 54 paired cases',
        transform=ax.transAxes, color=MUTED, fontsize=8.5)
save(fig, 'figR3_03_paired_delta')
paired_tbl = pd.DataFrame(rows)
display(paired_tbl)

# Original notebook cell 11
# Figure R3-4 — the same pairing without the mean: who wins each individual case.
# A case is a tie when the two systems are within 0.25 of a point (a quarter of one criterion).
TIE = 0.25
j = paired('eff', 'both')
fig, ax = plt.subplots(figsize=(9.6, .62 * NG + 2.3))
y = np.arange(NG)[::-1]
for yi, m in zip(y, GD_MODELS):
    d = j[j.model == m]['delta']
    parts = [(100 * (d < -TIE).mean(), SYS_COLOR['DOME'], 'DOME wins'),
             (100 * (d.abs() <= TIE).mean(), TIE_COLOR, 'tie'),
             (100 * (d > TIE).mean(), SYS_COLOR['Claude Code'], 'Claude Code wins')]
    left = 0
    for v, col, _ in parts:
        ax.barh(yi, v, .62, left=left, color=col, edgecolor=SURFACE, linewidth=2)
        if v >= 7:
            ax.text(left + v / 2, yi, f'{v:.0f}', ha='center', va='center',
                    fontsize=8.5, color=ink_on(col))
        left += v
ax.set_yticks(y, [m for m in GD_MODELS]); ax.set_xlim(0, 100)
ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
ax.set_xlabel('Share of the 54 matched test cases'); ax.grid(False)
ax.legend(handles=[Patch(facecolor=SYS_COLOR['DOME'], label='DOME wins'),
                   Patch(facecolor=TIE_COLOR, label=f'tie (within {TIE:g} pt)'),
                   Patch(facecolor=SYS_COLOR['Claude Code'], label='Claude Code wins')],
          ncol=3, loc='upper center', bbox_to_anchor=(.5, -.16))
ax.set_title('RQ3 — case-by-case outcome vs. each DOME model')
ax.text(0, 1.03, 'effective quality, both DOME modes averaged per case',
        transform=ax.transAxes, color=MUTED, fontsize=8.5)
save(fig, 'figR3_04_win_tie_loss')

# Original notebook cell 12
# Figure R3-5 — DOME is a framework, not a model: its per-case CEILING is the best of the
# ten configurations it can run. That is the honest upper bound of "adopt DOME and pick well".
gd = ctx[ctx.system == 'DOME'].groupby('case')['eff']
comp = pd.DataFrame({'best': gd.max(), 'mean': gd.mean(), 'worst': gd.min()}).join(
    CC_CASE['eff'].rename('claude')).join(CC_CASE['task']).dropna()
order = comp.sort_values('claude', kind='stable').index

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.4, 4.6), gridspec_kw=dict(width_ratios=[1.9, 1]))
xs = np.arange(len(order))
cl, bs = comp.loc[order, 'claude'].values, comp.loc[order, 'best'].values
a1.fill_between(xs, cl, bs, where=cl >= bs, interpolate=True, linewidth=0,
                color=SYS_COLOR['Claude Code'], alpha=.20, label='Claude Code ahead')
a1.fill_between(xs, cl, bs, where=cl < bs, interpolate=True, linewidth=0,
                color=SYS_COLOR['DOME'], alpha=.20, label='DOME ahead')
a1.plot(xs, bs, color=SYS_COLOR['DOME'], lw=2, label='DOME — best of its 10 configs')
a1.plot(xs, cl, color=SYS_COLOR['Claude Code'], lw=2, label='Claude Code')
a1.set_xlim(-.5, len(order) - .5); a1.set_ylim(.8, 6.4); a1.set_yticks(range(1, 6))
a1.set_xlabel('The 54 test cases, ordered by Claude Code score'); a1.set_ylabel('Effective quality (1–5)')
a1.set_xticks([]); ygrid(a1); a1.legend(fontsize=8.5, loc='upper left', ncol=2)
a1.set_title('Per case', fontsize=10.5)

pairs = [('best', 'DOME\nbest config'), ('mean', 'DOME\nmean config'),
         ('worst', 'DOME\nworst config')]
for i, (c, lbl) in enumerate(pairs):
    d = comp['claude'] - comp[c]
    p = stats.wilcoxon(comp['claude'], comp[c]).pvalue
    e = ci95(d)
    a2.bar(i, d.mean(), .55, yerr=e, capsize=3, color=SYS_COLOR['Claude Code'],
           error_kw=dict(ecolor=INK_2, lw=1))
    top = (d.mean() + e + .10) if d.mean() >= 0 else (d.mean() - e - .10)
    a2.text(i, top, f'{d.mean():+.2f}\n{pstar(p)}', ha='center',
            va='bottom' if d.mean() >= 0 else 'top', fontsize=8.5, color=INK_2, linespacing=1.35)
a2.axhline(0, color=INK, lw=1.2)
a2.set_xticks(range(len(pairs)), [l for _, l in pairs], fontsize=8.5)
a2.set_ylim(-2.1, 3.6); ygrid(a2)
a2.set_ylabel('Claude Code − DOME'); a2.set_title('Paired mean', fontsize=10.5)
head(fig, 'RQ3 — Claude Code against the DOME configuration space',
     'DOME can be configured 10 ways per case (5 models x direct/tool calling); Claude Code has one')
save(fig, 'figR3_05_configuration_ceiling')
display(comp.groupby('task')[['claude', 'best', 'mean', 'worst']].mean().round(2))

# Original notebook cell 13
# Figure R3-6 — is the ranking stable across projects? (effective quality, model x repo)
piv = (ctx.pivot_table(index='model', columns='repo', values='eff', aggfunc='mean', observed=True)
          .reindex(index=MODEL_ORDER, columns=REPO_ORDER))
piv.columns = [REPO_LABEL[c] for c in piv.columns]
fig, ax = plt.subplots(figsize=(8.6, .55 * NM + 1.4))
im = ax.imshow(piv.values, cmap=SEQ, vmin=1, vmax=5, aspect='auto')
for i in range(piv.shape[0]):
    for j_ in range(piv.shape[1]):
        v = piv.values[i, j_]
        if np.isfinite(v):
            ax.text(j_, i, f'{v:.1f}', ha='center', va='center', fontsize=9.5,
                    color='white' if v > 3.2 else INK)
ax.axhline(NG - .5, color=INK, lw=2)                     # DOME above, Claude Code below
ax.set_xticks(range(piv.shape[1]), piv.columns, rotation=20, ha='right')
ax.set_yticks(range(piv.shape[0]), piv.index); ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=.03, pad=.02); cb.outline.set_visible(False)
cb.set_label('Effective quality (1–5)', color=INK_2, fontsize=9)
ax.set_title('RQ3 — quality per project')
save(fig, 'figR3_06_quality_by_repo')

# Original notebook cell 14
# Figure R3-7 — the shape behind the means: full 1-5 distribution at annotation level.
d = ann.copy()
for dim in DIM_EN:
    d[dim] = d[dim].where(~d.failed, 1)                  # failed run = 1 on every criterion
fig, axes = plt.subplots(2, 2, figsize=(11.5, 5.8), sharex=True)
for ax, dim in zip(axes.ravel(), DIM_EN):
    ct = (pd.crosstab(d['model'], d[dim], normalize='index') * 100).reindex(MODEL_ORDER)
    left = np.zeros(len(ct))
    for s in [1, 2, 3, 4, 5]:
        v = ct[s].values if s in ct else np.zeros(len(ct))
        ax.barh(range(len(ct)), v, left=left, height=.62, color=LIKERT_COLOR[s],
                edgecolor=SURFACE, linewidth=2)
        for y, (val, l) in enumerate(zip(v, left)):
            if val >= 7:
                ax.text(l + val / 2, y, f'{val:.0f}', ha='center', va='center',
                        fontsize=8, color=LIKERT_INK[s])
        left += v
    ax.set_yticks(range(len(ct)), [MODEL_SHORT[m].replace('\n', ' ') for m in ct.index], fontsize=8)
    ax.axhline(NG - .5, color=INK, lw=1.4)
    ax.set_title(dim, fontsize=11); ax.set_xlim(0, 100); ax.invert_yaxis()
    ax.grid(False); ax.tick_params(labelsize=9)
    for sp_ in ('left', 'bottom'):
        ax.spines[sp_].set_visible(False)
    ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
fig.legend(handles=[Patch(facecolor=LIKERT_COLOR[s], label=f'{s}') for s in [1, 2, 3, 4, 5]],
           ncol=5, loc='lower center', bbox_to_anchor=(.5, -.11), title='Rating (1 = worst, 5 = best)')
head(fig, 'RQ3 — rating distribution per criterion',
     'annotation level (2 per context), failed runs scored 1 · the line separates DOME from Claude Code')
save(fig, 'figR3_07_rating_distribution')

# Original notebook cell 16
# Figure R3-8 — how often each system returns nothing, and what that costs it.
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.4, 4.4), gridspec_kw=dict(width_ratios=[1, 1.25]))
fr = ctx.groupby('model', observed=True)['failed'].agg(['mean', 'sum', 'size']).reindex(MODEL_ORDER)
bars = a1.bar(range(NM), fr['mean'] * 100, .6, color=[MODEL_COLOR[m] for m in MODEL_ORDER])
for b, (_, r) in zip(bars, fr.iterrows()):
    a1.text(b.get_x() + b.get_width() / 2, b.get_height() + .8,
            f"{r['mean']*100:.0f}%\n({int(r['sum'])}/{int(r['size'])})", ha='center',
            fontsize=8.5, color=INK_2)
a1.axvline(NG - .5, color=AXIS, lw=1.2, zorder=0)
a1.set_xticks(range(NM), MODEL_TICKS, fontsize=7.5)
a1.set_ylim(0, max(35, fr['mean'].max() * 130)); a1.set_ylabel('Runs with empty output (%)')
ygrid(a1); a1.set_title('Failure rate', fontsize=10.5)

x, w = np.arange(NM), .38
cond = [ctxv[ctxv.model == m]['Overall'].mean() for m in MODEL_ORDER]
eff = [ctx[ctx.model == m]['eff'].mean() for m in MODEL_ORDER]
b1 = a2.bar(x - w / 2, cond, w * .9, color=[MODEL_COLOR[m] for m in MODEL_ORDER])
b2 = a2.bar(x + w / 2, eff, w * .9, color=[MODEL_COLOR[m] for m in MODEL_ORDER], alpha=.42,
            hatch='//', edgecolor=SURFACE)
barlabels(a2, list(b1) + list(b2), dy=.08)
for xi, c_, e_ in zip(x, cond, eff):
    a2.annotate('', xy=(xi + w / 2, e_), xytext=(xi - w / 2, c_),
                arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=1, shrinkA=2, shrinkB=2))
a2.axvline(NG - .5, color=AXIS, lw=1.2, zorder=0)
a2.axhline(3, color=AXIS, lw=1, ls='--', zorder=0)
a2.set_xticks(x, MODEL_TICKS, fontsize=7.5); a2.set_ylim(1, 5.2); a2.set_yticks(range(1, 6))
a2.set_ylabel('Quality (1–5)'); ygrid(a2)
a2.legend(handles=[Patch(facecolor=MUTED, label='conditional (failures excluded)'),
                   Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE,
                         label='effective (failures = 1)')],
          ncol=2, loc='upper center', bbox_to_anchor=(.5, -.20), fontsize=8.5)
a2.set_title('What unreliability costs', fontsize=10.5)
head(fig, 'RQ3 — reliability',
     'the arrow is the drop a maintainer actually experiences: the longer it is, the less the headline quality means')
save(fig, 'figR3_08_reliability')

# Original notebook cell 18
# Figure R3-9 — what an agentic loop costs in tokens. Log scale: the systems differ by ~20x.
parts = [('input_tokens', 'input', 1.0, None), ('output_tokens', 'output', .70, '//'),
         ('cache_write_tokens', 'cache write', .45, 'xx'), ('cache_read_tokens', 'cache read', .22, '..')]
g = ctx.groupby('model', observed=True)[[p[0] for p in parts]].mean().reindex(MODEL_ORDER)
fig, (ax, a2) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1.55, 1]))
bottom = np.zeros(NM)
for c, lbl, alpha, hatch in parts:
    v = g[c].fillna(0).values
    ax.bar(range(NM), v, .58, bottom=bottom, color=[MODEL_COLOR[m] for m in MODEL_ORDER],
           alpha=alpha, hatch=hatch, edgecolor=SURFACE, linewidth=1.5)
    bottom += v

# right panel: the same stack as a share of the total. Cache reads are billed at a fraction of
# fresh input tokens, so the absolute panel alone would overstate what the agentic loop costs.
share = g.div(bottom, axis=0) * 100
left = np.zeros(NM)
for c, lbl, alpha, hatch in parts:
    v = share[c].fillna(0).values
    a2.barh(range(NM), v, .58, left=left, color=[MODEL_COLOR[m] for m in MODEL_ORDER],
            alpha=alpha, hatch=hatch, edgecolor=SURFACE, linewidth=1.5)
    for yy, (val, l) in enumerate(zip(v, left)):
        if val >= 9:
            # the segment is alpha-blended onto the surface, so pick the ink from the blend
            blend = (alpha * np.array(mpl.colors.to_rgb(MODEL_COLOR[MODEL_ORDER[yy]]))
                     + (1 - alpha) * np.array(mpl.colors.to_rgb(SURFACE)))
            a2.text(l + val / 2, yy, f'{val:.0f}', ha='center', va='center',
                    fontsize=8, color=ink_on(tuple(blend)))
    left += v
a2.set_yticks(range(NM), [MODEL_SHORT[m].replace('\n', ' ') for m in MODEL_ORDER], fontsize=8)
a2.invert_yaxis(); a2.set_xlim(0, 100); a2.grid(False)
a2.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
a2.set_xlabel('Share of that run’s tokens'); a2.set_title('Composition', fontsize=10.5)
for sp_ in ('left', 'bottom'):
    a2.spines[sp_].set_visible(False)
ref = bottom[MODEL_ORDER.index('Gemini 3.1 Flash-Lite')]
for i, tot in enumerate(bottom):
    lab = f'{tot:,.0f}' + (f'\n{tot / ref:.1f}x Gemini' if MODEL_ORDER[i] == CC else '')
    ax.text(i, tot + bottom.max() * .02, lab, ha='center', fontsize=9, color=INK_2,
            fontweight='bold', linespacing=1.35)
ax.axvline(NG - .5, color=AXIS, lw=1.2, zorder=0)
ax.set_ylim(0, bottom.max() * 1.22)
ax.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))
ax.set_xticks(range(NM), MODEL_TICKS, fontsize=8)
ax.set_ylabel('Tokens per run (mean)'); ygrid(ax); ax.set_title('Absolute', fontsize=10.5)
fig.legend(handles=[Patch(facecolor=MUTED, alpha=a, hatch=h, edgecolor=SURFACE, label=l)
                    for _, l, a, h in parts], ncol=4, loc='lower center', bbox_to_anchor=(.5, -.07))
head(fig, 'RQ3 — token consumption per run',
     'stacked parts sum exactly to total_tokens · linear axis, so segment heights are comparable')
save(fig, 'figR3_09_tokens')
display(g.assign(total=bottom).round(0))

# Original notebook cell 19
# Figure R3-10 — response time, per task. Same latency field for both systems.
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharey=True)
for ax, t in zip(axes, TASK_ORDER):
    d = ctxv[ctxv.task == t]
    data = [d[d.model == m]['latency_seconds'].dropna().values for m in MODEL_ORDER]
    bp = ax.boxplot(data, patch_artist=True, widths=.55, showfliers=False,
                    medianprops=dict(color=INK, lw=2), whiskerprops=dict(color=AXIS),
                    capprops=dict(color=AXIS), boxprops=dict(edgecolor=SURFACE, lw=2))
    for patch, m in zip(bp['boxes'], MODEL_ORDER):
        patch.set_facecolor(MODEL_COLOR[m]); patch.set_alpha(.55)
    for i, v in enumerate(data, start=1):
        if len(v):
            ax.text(i, np.percentile(v, 75), f'{np.median(v):.0f}s', ha='center', va='bottom',
                    fontsize=8, color=INK_2)
    ax.axvline(NG + .5, color=AXIS, lw=1.2, zorder=0)
    ax.set_xticks(range(1, NM + 1), MODEL_TICKS, fontsize=7.5)
    ax.set_title(TASK_SHORT[t], fontsize=10.5); ygrid(ax)
axes[0].set_ylabel('Response time per run (s)')
head(fig, 'RQ3 — response time', 'box = IQR, line = median, whiskers = 1.5·IQR (outliers hidden) · valid runs only')
save(fig, 'figR3_10_response_time')

# Original notebook cell 20
# Figures R3-11 — the trade-off that answers RQ3 in one picture: quality against what it costs.
def frontier(ax, pts):
    # Pareto set for (minimise x, maximise y): keep a point only if nothing cheaper is better
    best, keep = -np.inf, []
    for xx, yy in sorted(pts):
        if yy > best:
            keep.append((xx, yy)); best = yy
    if len(pts) >= 4 and len(keep) > 1:
        ax.step(*zip(*keep), where='post', color=AXIS, lw=1.4, ls='--', zorder=0)

MARKERS = ['o', 's', '^', 'D', 'P', '*']
agg = (ctx.groupby('model', observed=True)
          .agg(q=('eff', 'mean'), tok=('total_tokens', 'mean'), t=('latency_seconds', 'mean'))
          .reindex(MODEL_ORDER).reset_index())
fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.9))
for ax, (xc, xlabel, logx) in zip(axes, [('tok', 'Mean total tokens per run', True),
                                         ('t', 'Mean response time per run (s)', False)]):
    for i, m in enumerate(MODEL_ORDER):
        r = agg[agg.model == m].iloc[0]
        ax.scatter(r[xc], r['q'], s=300 if m != CC else 460, color=MODEL_COLOR[m], marker=MARKERS[i],
                   alpha=.9, edgecolor=SURFACE, linewidth=2, zorder=3, label=m)
        ax.annotate(MODEL_SHORT[m].replace('\n', ' '), (r[xc], r['q']), textcoords='offset points',
                    xytext=(0, 15), ha='center', fontsize=8, color=INK_2)
    frontier(ax, [(r[xc], r['q']) for _, r in agg.iterrows()])
    if logx:
        ax.set_xscale('log')
    ax.margins(x=.20)                    # direct labels sit outside the marks; give them room
    ax.set_xlabel(xlabel); ax.set_ylabel('Effective quality (1–5)')
    ax.set_ylim(1.5, 4.6); ax.set_yticks(range(2, 5))
    ax.grid(True, which='major'); ax.set_axisbelow(True)
head(fig, 'RQ3 — quality against cost',
     'dashed step = Pareto frontier (nothing cheaper scores higher) · marker shape backs up hue')
save(fig, 'figR3_11_quality_vs_cost')
display(agg.assign(q_per_10k_tok=(agg.q / (agg.tok / 10000)).round(2)).round(2))

# Original notebook cell 22
# 4.1 — build the coding corpus (run once, then code by hand)
CODEBOOK = {
    'missed_changes':   ['não descreve', 'nao descreve', 'não documenta', 'nao documenta', 'não menciona',
                         'nao menciona', 'faltou', 'falta ', 'não contempla', 'não cobre', 'deixou de',
                         'não informa', 'incompleto', 'não abrange'],
    'hallucination':    ['não existe', 'nao existe', 'inventou', 'alucin', 'não corresponde', 'nao corresponde',
                         'não condiz', 'não bate', 'errado', 'incorret', 'não é verdade', 'não reflete'],
    'empty_or_noop':    ['vazio', 'nada relevante', 'não gerou', 'nao gerou', 'sem conteúdo', 'não trouxe',
                         'nenhuma alteração', 'nenhuma informação', 'não apresentou'],
    'wrong_format':     ['formato', 'diff', 'cabeçalho', 'cabecalho', 'markdown', 'não é um readme',
                         'não é um changelog', '.sln', 'estrutura', 'bagunç', 'sintaxe'],
    'verbose_repeated': ['repet', 'verboso', 'prolixo', 'muito longo', 'extenso', 'duplicad', 'redundan',
                         'detalhad', 'tecnico demai', 'técnico demai'],
    'too_generic':      ['genéric', 'generic', 'vago', 'superficial', 'raso', 'óbvio', 'obvio', 'não detalha'],
    'truncated':        ['truncad', 'cortad', 'interromp', 'incompleta no final', 'pela metade'],
    'confusing':        ['confus', 'não faz sentido', 'nao faz sentido', 'difícil de entender', 'não entendi',
                         'não ficou claro', 'nao ficou claro', 'ilegível'],
    'wrong_language':   ['inglês', 'ingles', 'português', 'portugues', 'idioma', 'traduz'],
    'meta_leakage':     ['prompt', 'instrução', 'instrucao', 'meta', 'explicação do modelo', 'comentário do modelo'],
    'irrelevant':       ['irrelevante', 'não relevante', 'fora de contexto', 'nada a ver', 'não tem relação'],
}

def seed_codes(t):
    hits = [c for c, kws in CODEBOOK.items() if any(k in str(t).lower() for k in kws)]
    return ';'.join(hits) if hits else 'uncoded'

rows = []
for dim in DIM_EN:
    sub = ann[(ann[dim] <= 2) & ann['cmt_' + dim].notna()]
    for _, r in sub.iterrows():
        rows.append(dict(uid=r.uid, system=r.system, model=r.model, repo=r.repo, case=r.case,
                         task=r.task, user_id=r.user_id, criterion=dim, score=r[dim],
                         comment=str(r['cmt_' + dim]).strip()))
low = pd.DataFrame(rows)
low['code_auto'] = low['comment'].map(seed_codes)
low['code_final'] = ''
low.to_csv('rq3_low_score_comments_TO_CODE.csv', index=False)
print(f'{len(low)} low-score comments exported to rq3_low_score_comments_TO_CODE.csv')
display(low.groupby('system').agg(comments=('comment', 'size'), contexts=('uid', 'nunique')))

# Original notebook cell 23
# 4.2 — Figure R3-12: do the two systems fail for the same reasons?
CODED = os.path.join(DATA_DIR, 'rq3_low_score_comments_CODED.csv')
if os.path.exists(CODED):
    low, src = pd.read_csv(CODED), 'code_final'
    print('using MANUAL codes from', CODED)
else:
    src = 'code_auto'
    print('!! no coded file found — figure R3-12 uses the KEYWORD SEEDS.')
    print('   Code rq3_low_score_comments_TO_CODE.csv by hand and save it as', CODED)

lc = (low.assign(code=low[src].fillna('').replace('', 'uncoded').astype(str).str.split(';'))
         .explode('code').reset_index(drop=True))
lc['code'] = lc['code'].str.strip()
lc = lc[lc.code.ne('') & lc.code.ne('uncoded')]

n_gd = low[low.system == 'DOME']['comment'].nunique()
n_cc = low[low.system == 'Claude Code']['comment'].nunique()
share = pd.DataFrame({
    'DOME': lc[lc.system == 'DOME'].groupby('code')['comment'].nunique() / max(n_gd, 1) * 100,
    'Claude Code': lc[lc.system == 'Claude Code'].groupby('code')['comment'].nunique() / max(n_cc, 1) * 100,
}).fillna(0)
share = share.loc[share.max(axis=1).sort_values().index]

fig, ax = plt.subplots(figsize=(9.6, .46 * len(share) + 2.2))
y = np.arange(len(share))
ax.barh(y, -share['DOME'], .62, color=SYS_COLOR['DOME'], label='DOME')
ax.barh(y, share['Claude Code'], .62, color=SYS_COLOR['Claude Code'], label='Claude Code')
for yy, (a_, b_) in enumerate(zip(share['DOME'], share['Claude Code'])):
    if a_ > 0:
        ax.text(-a_ - 1.2, yy, f'{a_:.0f}%', va='center', ha='right', fontsize=8.5, color=INK_2)
    if b_ > 0:
        ax.text(b_ + 1.2, yy, f'{b_:.0f}%', va='center', ha='left', fontsize=8.5, color=INK_2)
lim = max(share.max().max() * 1.35, 5)
ax.set_xlim(-lim, lim); ax.set_yticks(y, [c.replace('_', ' ') for c in share.index])
ax.set_xticks(ax.get_xticks(), [f'{abs(t):.0f}%' for t in ax.get_xticks()])
ax.axvline(0, color=AXIS, lw=1); xgrid(ax)
ax.set_xlabel('Share of that system’s low-score comments carrying the code')
ax.legend(ncol=2, loc='upper center', bbox_to_anchor=(.5, -.13))
ax.set_title('RQ3 — reasons behind low ratings')
ax.text(0, 1.02, f'n = {n_gd} DOME vs {n_cc} Claude Code comments on ratings ≤ 2, '
                 'each normalised within its system · a comment may carry several codes',
        transform=ax.transAxes, color=MUTED, fontsize=8.5)
save(fig, 'figR3_12_low_score_codes')

# Original notebook cell 25
# 5.1 — one row per system/model: the whole RQ3 story in a table
summary = (ctx.groupby(['system', 'model'], observed=True)
             .agg(n=('uid', 'size'), cases=('case', 'nunique'),
                  fail_pct=('failed', lambda s: 100 * s.mean()),
                  eff_quality=('eff', 'mean'),
                  tokens=('total_tokens', 'mean'), latency_s=('latency_seconds', 'mean'),
                  cost_usd=('total_cost', 'mean'))
             .join(ctxv.groupby(['system', 'model'], observed=True)
                     .agg(**{d: (d, 'mean') for d in DIM_EN},
                          cond_quality=('Overall', 'mean')))
             .dropna(how='all').round(2))
display(summary)
summary.to_csv(f'{FIGDIR}/rq3_summary_by_model.csv')

by_task = (ctx.groupby(['task', 'system', 'model'], observed=True)
             .agg(n=('uid', 'size'), fail_pct=('failed', lambda s: 100 * s.mean()),
                  eff_quality=('eff', 'mean'), tokens=('total_tokens', 'mean'),
                  latency_s=('latency_seconds', 'mean'))
             .dropna(subset=['eff_quality']).round(2))
display(by_task)
by_task.to_csv(f'{FIGDIR}/rq3_summary_by_task.csv')

# the paired tests, in one table (this is what section 5.4 should cite)
rows = []
for mode in ('both', 'direct', 'tool'):
    j = paired('eff', mode)
    for m in GD_MODELS:
        jj = j[j.model == m]
        rows.append(dict(gd_mode=mode, comparator=m, n_cases=len(jj),
                         claude=round(jj['cc'].mean(), 2), dome=round(jj['gd'].mean(), 2),
                         delta=round(jj['delta'].mean(), 2),
                         cliffs_delta=round(cliffs_delta(jj['cc'], jj['gd']), 2),
                         wilcoxon_p=wilcoxon(jj)))
gd = ctx[ctx.system == 'DOME'].groupby('case')['eff']
for label, s in [('best config per case', gd.max()), ('mean config per case', gd.mean())]:
    jj = pd.DataFrame({'gd': s}).join(CC_CASE['eff'].rename('cc')).dropna()
    rows.append(dict(gd_mode='oracle', comparator=label, n_cases=len(jj),
                     claude=round(jj['cc'].mean(), 2), dome=round(jj['gd'].mean(), 2),
                     delta=round((jj['cc'] - jj['gd']).mean(), 2),
                     cliffs_delta=round(cliffs_delta(jj['cc'], jj['gd']), 2),
                     wilcoxon_p=stats.wilcoxon(jj['cc'], jj['gd']).pvalue))
paired_tests = pd.DataFrame(rows)
display(paired_tests)
paired_tests.to_csv(f'{FIGDIR}/rq3_paired_tests.csv', index=False)
print('\nfigures written:'); print('\n'.join(sorted(os.listdir(FIGDIR))))

# Additional machine-readable exports; no change to the analysis.
ann.to_csv('figs_rq3/annotations.csv', index=False)
ctx.to_csv('figs_rq3/contexts.csv', index=False)
