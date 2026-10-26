"""Adapted from the supplied analysis notebook; see docs/methodology.md."""
from pathlib import Path
import os
import matplotlib
matplotlib.use('Agg')
display = print

# Original notebook cell 3
# 0.2 — imports, palette, plotting defaults
import os, re, glob, json, itertools, textwrap
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

os.makedirs('figs', exist_ok=True)

# --- palette -------------------------------------------------------------
# Categorical slots for the 5 models. The first 4 hues were validated all-pairs on a
# light surface: worst CVD dE 9.2 (deutan), worst normal-vision dE 16.3; the amber slot
# added for GPT-5.6 Luna is CAT8's 4th, validated on the adjacent pairlist. Assigned by
# entity in a FIXED order -- never cycled, never re-assigned when a model is filtered out.
# New models are APPENDED so the hue of an existing model never moves between runs.
SURFACE   = '#fcfcfb'
INK       = '#0b0b0b'
INK_2     = '#52514e'
MUTED     = '#898781'
GRID      = '#e1e0d9'
AXIS      = '#c3c2b7'

MODEL_ORDER = ['Gemini 3.1 Flash-Lite', 'Llama 3.1 8B', 'Mistral-Nemo 12B', 'Qwen2.5-Coder 14B',
               'GPT-5.6 Luna']
MODEL_COLOR = dict(zip(MODEL_ORDER, ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#eda100']))
NM = len(MODEL_ORDER)                # every model axis is sized from this, never hard-coded
# tick labels: full names no longer fit in 5 slots, so every model axis uses these
MODEL_SHORT = {'Gemini 3.1 Flash-Lite': 'Gemini\n3.1 FL', 'Llama 3.1 8B': 'Llama\n3.1 8B',
               'Mistral-Nemo 12B': 'Mistral\nNemo 12B', 'Qwen2.5-Coder 14B': 'Qwen2.5\nCoder 14B',
               'GPT-5.6 Luna': 'GPT-5.6\nLuna'}
MODEL_TICKS = [MODEL_SHORT[m] for m in MODEL_ORDER]
# self-hosted (Ollama) models: billed $0 by a provider, but not free -- see figure 15
SELF_HOSTED = {'Llama 3.1 8B', 'Mistral-Nemo 12B', 'Qwen2.5-Coder 14B'}

# Diverging ramp for the 1-5 Likert scale (blue<->red, neutral gray midpoint).
# Each arm validated as a one-hue ordinal ramp (monotone L, dL>=0.06, light end >=2:1).
LIKERT_COLOR = {1: '#b03434', 2: '#e88a86', 3: '#c3c2b7', 4: '#86b6ef', 5: '#1c5cab'}
LIKERT_INK   = {1: 'white',   2: INK,       3: INK,       4: INK,       5: 'white'}

# Eight-slot categorical palette, for the qualitative codes in section 3. Validated on the
# *adjacent* pairlist, which is what a stacked bar needs.
CAT8 = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']

# Sequential ramp (single hue, light->dark) for heatmaps.
SEQ = mpl.colors.LinearSegmentedColormap.from_list(
    'ghd_blue', ['#cde2fb', '#9ec5f4', '#5598e7', '#2a78d6', '#256abf', '#184f95', '#0d366b'])

# Status colors -- reserved, never used as a series color.
ST_CRITICAL, ST_GOOD = '#d03b3b', '#0ca30c'

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
    # multi-panel figures: title + grey subtitle above the panels, spaced in inches so the
    # gap does not shrink when the figure is short
    H = fig.get_figheight()
    fig.suptitle(title, x=.02, ha='left', va='top', y=1 - .12 / H, fontweight='bold', fontsize=12)
    if sub:
        fig.text(.02, 1 - .40 / H, sub, color=MUTED, fontsize=8.5, va='top')
    fig._head = (.66 if sub else .44) / H

def save(fig, name):
    # every figure lands as PNG (slides/preview) and PDF (LaTeX)
    fig.tight_layout(rect=[0, 0, 1, 1 - getattr(fig, '_head', 0)])
    for ext in ('png', 'pdf'):
        fig.savefig(f'figs/{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  -> figs/{name}.png | .pdf')

def ink_on(color):
    # label ink that survives on top of a filled mark (yellow needs dark ink, navy needs white)
    r, g, b = mpl.colors.to_rgb(color)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return INK if lum > 0.5 else 'white'

def ygrid(ax):
    ax.set_axisbelow(True); ax.grid(axis='y', which='major'); ax.grid(axis='x', visible=False)

def xgrid(ax):
    ax.set_axisbelow(True); ax.grid(axis='x', which='major'); ax.grid(axis='y', visible=False)

def model_legend(ax, models=None, **kw):
    models = models or MODEL_ORDER
    ax.legend(handles=[Patch(facecolor=MODEL_COLOR[m], label=m) for m in models], **kw)

print('setup ok')

# Original notebook cell 4
DATA_DIR = os.environ['DOME_DATA_DIR']
paths = sorted(glob.glob(os.path.join(DATA_DIR, '*_answers_merged.csv.gz')))


# Original notebook cell 5
# 0.4 — load, normalise, build the two analysis tables
DIMS = {'Concisão': 'Conciseness', 'Corretude': 'Correctness',
        'Completude': 'Completeness', 'Clareza': 'Clarity'}
DIM_EN = list(DIMS.values())

MODEL_LABEL = {'gemini-3.1-flash-lite': 'Gemini 3.1 Flash-Lite', 'llama3.1:8b': 'Llama 3.1 8B',
               'mistral-nemo:12b': 'Mistral-Nemo 12B', 'qwen2.5-coder:14b': 'Qwen2.5-Coder 14B',
               'gpt-5.6-luna': 'GPT-5.6 Luna'}
TASK_LABEL  = {'readme/readme': 'README (generation)', 'readme-update/readme_update': 'README (update)',
               'changelog/changelog': 'CHANGELOG'}
TASK_RQ     = {'README (generation)': 'RQ1', 'README (update)': 'RQ1', 'CHANGELOG': 'RQ2'}
RQ_TITLE    = {'RQ1': 'RQ1 — README generation & update', 'RQ2': 'RQ2 — CHANGELOG generation'}
TASK_ORDER  = ['README (generation)', 'README (update)', 'CHANGELOG']

NUMCOLS = ['input_tokens', 'output_tokens', 'total_tokens', 'cache_read_tokens', 'cache_write_tokens',
           'total_cost', 'num_observations', 'eval_duration_s', 'load_duration_s', 'total_duration_s',
           'prompt_eval_duration_s', 'metadata_execution_time_seconds']

frames = []
for p in paths:
    r = pd.read_csv(p, low_memory=False)
    r['repo'] = os.path.basename(p).replace('_answers_merged.csv.gz', '')
    frames.append(r)
raw = pd.concat(frames, ignore_index=True)

# A run failed when the trace returned nothing or errored out. `is_filler` marks the empty
# ones for the Ollama/Gemini exports, but the GPT-5.6 Luna export never set the flag, so
# derive it from the trace: null output ("Valor Nulo") or a non-empty error message.
_out = raw['C : output'].astype(str).str.strip()
FAILED = (raw['is_filler'].astype(bool) | _out.isin(['Valor Nulo', 'nan', ''])
          | raw['C : metadata_error_message'].astype(str).str.strip()
                .replace('Valor Nulo', '').astype(bool))

# annotation-level table: one row per (context, annotator)
ann = pd.DataFrame({
    'repo':      raw['repo'],
    'context_id': raw['context_id'],
    'user_id':   raw['user_id'],
    'model':     raw['C : metadata_model_name'].map(MODEL_LABEL),
    'task':      raw['C : metadata_test_type'].map(TASK_LABEL),
    'config':    pd.to_numeric(raw['C : metadata_config_index'], errors='coerce'),
    'tool_calling': raw['C : is_tool_calling'].astype(str).str.lower().eq('true'),
    # nullable boolean: "Valor Nulo" -> pd.NA (plain object dtype would break `~mask`)
    'commit_mixed': raw['C : metadata_commit_mixed'].astype(str).str.lower()
                       .map({'true': True, 'false': False}).astype('boolean'),
    'failed':    FAILED,                                   # RUN FAILURE, auto-scored 1
    'out_chars': pd.to_numeric(raw['C : output_char_count']).where(~FAILED),
})
ann['rq'] = ann['task'].map(TASK_RQ)
ann['uid'] = ann['repo'] + '#' + ann['context_id'].astype(str)     # unique context key

for c in NUMCOLS:
    ann[c] = pd.to_numeric(raw['C : ' + c], errors='coerce')       # "Valor Nulo" -> NaN
ann.rename(columns={'metadata_execution_time_seconds': 'runtime_s'}, inplace=True)

for pt, en in DIMS.items():
    ann[en] = pd.to_numeric(raw['Q : ' + pt], errors='coerce')
    ann['cmt_' + en] = raw['Q : Justifique sua classificação de ' + pt]
ann['Overall'] = ann[DIM_EN].mean(axis=1)

# context-level table: the two annotators averaged; this is the unit of analysis
meta = ['repo', 'context_id', 'uid', 'model', 'task', 'rq', 'config', 'tool_calling',
        'commit_mixed', 'failed', 'out_chars'] + [c for c in NUMCOLS if c != 'metadata_execution_time_seconds'] + ['runtime_s']
ctx = (ann.groupby('uid', as_index=False)
          .agg({**{c: 'first' for c in meta if c != 'uid'},
                **{d: 'mean' for d in DIM_EN + ['Overall']},
                'user_id': 'nunique'})
          .rename(columns={'user_id': 'n_raters'}))
ctx['model'] = pd.Categorical(ctx['model'], MODEL_ORDER, ordered=True)
ann['model'] = pd.Categorical(ann['model'], MODEL_ORDER, ordered=True)

# "valid" = the model actually returned something. Failures are analysed separately (fig. 4).
ctxv, annv = ctx[~ctx.failed].copy(), ann[~ann.failed].copy()

print(f'{len(ann)} annotations | {len(ctx)} contexts | {ctx.failed.sum()} failed ({ctx.failed.mean():.1%})')
display(pd.crosstab([ctx.task, ctx.model], ctx.failed, rownames=['task', 'model'], colnames=['failed']))

# Original notebook cell 6
# 0.5 — shared helpers used across sections
def ci95(s):
    # half-width of the 95% CI of the mean; 0 when n<2
    s = pd.Series(s).dropna()
    return 0.0 if len(s) < 2 else stats.t.ppf(0.975, len(s) - 1) * s.sem()

def rq_frames(valid=True):
    # yields (rq_key, subset) for RQ1 then RQ2
    src = ctxv if valid else ctx
    for rq in ('RQ1', 'RQ2'):
        yield rq, src[src.rq == rq].copy()

def kruskal_by_model(d, col):
    # omnibus test across the models + Dunn post-hoc (Holm)
    import scikit_posthocs as sp
    groups = [g[col].dropna().values for _, g in d.groupby('model', observed=True) if g[col].notna().sum() > 1]
    if len(groups) < 2:
        return np.nan, None
    H, p = stats.kruskal(*groups)
    dunn = sp.posthoc_dunn(d.dropna(subset=[col]), val_col=col, group_col='model', p_adjust='holm')
    return p, dunn

def pstar(p):
    return '' if pd.isna(p) else ('p < 0.001' if p < .001 else f'p = {p:.3f}')

def barlabels(ax, bars, fmt='{:.2f}', dy=0.02, size=8):
    # value labels double as the relief required by the sub-3:1 contrast of some slots
    for b in bars:
        h = b.get_height()
        if np.isfinite(h):
            ax.text(b.get_x() + b.get_width() / 2, h + dy, fmt.format(h),
                    ha='center', va='bottom', fontsize=size, color=INK_2)
print('helpers ok')

# Original notebook cell 8
# Figure 1 — mean rating per criterion x model (95% CI)
# Solid bar: valid runs only. Hatched bar: the same mean with failed runs (empty output)
# counted as 1, which is the score a user actually gets. Gap between them = unreliability.
for rq, d in rq_frames():
    dall = ctx[ctx.rq == rq]                     # same subset, failures included
    fig, ax = plt.subplots(figsize=(11, 4.6))
    w, x = 0.8 / (2 * NM), np.arange(len(DIM_EN))
    for i, m in enumerate(MODEL_ORDER):
        for k, (g, alpha, hatch) in enumerate([(d[d.model == m], 1.0, None),
                                               (dall[dall.model == m], .42, '//')]):
            s = [g[dim].where(~g.failed, 1) for dim in DIM_EN]     # failed -> 1 on every criterion
            ax.bar(x + (2 * i + k - NM + .5) * w, [v.mean() for v in s], w * .88,
                   yerr=[ci95(v) for v in s], capsize=2, color=MODEL_COLOR[m], alpha=alpha,
                   hatch=hatch, edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
    ax.set_xticks(x, DIM_EN); ax.set_ylim(1, 5.4); ax.set_yticks(range(1, 6))
    ax.set_ylabel('Mean rating (1–5)'); ygrid(ax)
    ax.axhline(3, color=AXIS, lw=1, ls='--', zorder=0)
    ax.set_title(f'{RQ_TITLE[rq]} — quality by criterion')
    ax.text(0, 1.02, f'n = {len(d)} valid of {len(dall)} contexts, 2 annotators each · bars are 95% CI '
                     f'· dashed line = neutral (3)',
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    leg = ax.legend(handles=[Patch(facecolor=MUTED, label='failures excluded'),
                             Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE,
                                   label='failures counted as 1')], loc='upper right', fontsize=9)
    ax.add_artist(leg)                            # keep it when the model legend is drawn
    model_legend(ax, ncol=3, loc='upper center', bbox_to_anchor=(.5, -.12))
    save(fig, f'fig01_quality_by_criterion_{rq.lower()}')

    p, dunn = kruskal_by_model(d, 'Overall')
    print(f'{rq} Kruskal–Wallis on overall quality across models: {pstar(p)}')
    if dunn is not None:
        display(dunn.round(4))


# Original notebook cell 9
# Figure 2 — full 1-5 distribution (100% stacked), annotation level.
# Means hide the shape of this data: the ratings are bimodal (many 1s AND many 5s).
for rq, _ in rq_frames():
    d = annv[annv.rq == rq]
    fig, axes = plt.subplots(2, 2, figsize=(11, 5.6), sharex=True)
    for ax, dim in zip(axes.ravel(), DIM_EN):
        ct = (pd.crosstab(d['model'], d[dim], normalize='index') * 100).reindex(MODEL_ORDER)
        left = np.zeros(len(ct))
        for s in [1, 2, 3, 4, 5]:
            v = ct[s].values if s in ct else np.zeros(len(ct))
            ax.barh(ct.index, v, left=left, height=.62, color=LIKERT_COLOR[s],
                    edgecolor=SURFACE, linewidth=2)          # 2px surface gap between segments
            for y, (val, l) in enumerate(zip(v, left)):
                if val >= 7:
                    ax.text(l + val / 2, y, f'{val:.0f}', ha='center', va='center',
                            fontsize=8, color=LIKERT_INK[s])
            left += v
        ax.set_title(dim, fontsize=11); ax.set_xlim(0, 100); ax.invert_yaxis()
        ax.grid(False); ax.tick_params(labelsize=9)
        for sp_ in ('left', 'bottom'):
            ax.spines[sp_].set_visible(False)
        ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
    fig.legend(handles=[Patch(facecolor=LIKERT_COLOR[s], label=f'{s}') for s in [1, 2, 3, 4, 5]],
               ncol=5, loc='lower center', bbox_to_anchor=(.5, -.06), title='Rating (1 = worst, 5 = best)')
    head(fig, f'{RQ_TITLE[rq]} — distribution of individual ratings',
         f'n = {len(d)} ratings · share of ratings per model, % of row')
    save(fig, f'fig02_rating_distribution_{rq.lower()}')

# Original notebook cell 10
# Figure 3 — overall quality per model (box + jittered contexts)
rng = np.random.default_rng(0)
for rq, d in rq_frames():
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    data = [d[d.model == m]['Overall'].dropna().values for m in MODEL_ORDER]
    bp = ax.boxplot(data, patch_artist=True, widths=.55, showfliers=False,
                    medianprops=dict(color=INK, lw=2), whiskerprops=dict(color=AXIS),
                    capprops=dict(color=AXIS), boxprops=dict(edgecolor=SURFACE, lw=2))
    for patch, m in zip(bp['boxes'], MODEL_ORDER):
        patch.set_facecolor(MODEL_COLOR[m]); patch.set_alpha(.35)
    for i, (v, m) in enumerate(zip(data, MODEL_ORDER), start=1):
        ax.scatter(i + rng.uniform(-.16, .16, len(v)), v, s=14, color=MODEL_COLOR[m],
                   alpha=.75, edgecolor=SURFACE, linewidth=.5, zorder=3)
        ax.text(i, 5.35, f'n={len(v)}', ha='center', fontsize=8, color=MUTED)
    ax.set_xticks(range(1, NM + 1), MODEL_TICKS)
    ax.set_ylim(.8, 5.5); ax.set_yticks(range(1, 6)); ax.set_ylabel('Overall quality (mean of 4 criteria)')
    ygrid(ax)
    p, _ = kruskal_by_model(d, 'Overall')
    ax.set_title(f'{RQ_TITLE[rq]} — overall quality per model')
    ax.text(0, 1.02, f'each dot = one context · Kruskal–Wallis {pstar(p)}',
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    save(fig, f'fig03_overall_quality_box_{rq.lower()}')

# Original notebook cell 11
# Figure 4 — run failures (empty output) and their effect on the headline numbers.
# 19.4% of all runs returned nothing; ignoring them flatters the models that failed most.
for rq, _ in rq_frames():
    d = ctx[ctx.rq == rq]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw=dict(width_ratios=[1, 1.25]))

    fr = d.groupby('model', observed=True)['failed'].agg(['mean', 'sum', 'size']).reindex(MODEL_ORDER)
    bars = a1.bar(range(NM), fr['mean'] * 100, .6, color=[MODEL_COLOR[m] for m in MODEL_ORDER])
    for b, (_, r) in zip(bars, fr.iterrows()):
        a1.text(b.get_x() + b.get_width() / 2, b.get_height() + .8,
                f"{r['mean']*100:.0f}%\n({int(r['sum'])}/{int(r['size'])})", ha='center', fontsize=8.5, color=INK_2)
    a1.set_xticks(range(NM), MODEL_TICKS)
    a1.set_ylabel('Runs with empty output (%)'); a1.set_ylim(0, max(35, fr['mean'].max() * 130)); ygrid(a1)
    a1.set_title('Failure rate')

    w, x = .38, np.arange(NM)
    excl = [d[(d.model == m) & ~d.failed]['Overall'].mean() for m in MODEL_ORDER]
    # failed contexts already carry 1.0 on every criterion -- state it explicitly anyway
    eff  = [d[d.model == m]['Overall'].where(~d[d.model == m]['failed'], 1).mean() for m in MODEL_ORDER]
    b1 = a2.bar(x - w/2, excl, w*.9, color=[MODEL_COLOR[m] for m in MODEL_ORDER], label='failures excluded')
    b2 = a2.bar(x + w/2, eff,  w*.9, color=[MODEL_COLOR[m] for m in MODEL_ORDER], alpha=.42,
                hatch='//', edgecolor=SURFACE, label='failures counted as 1')
    barlabels(a2, list(b1) + list(b2), dy=.05)
    a2.set_xticks(x, MODEL_TICKS)
    a2.set_ylim(1, 5); a2.set_yticks(range(1, 6)); a2.set_ylabel('Overall quality (1–5)'); ygrid(a2)
    a2.legend(handles=[Patch(facecolor=MUTED, label='failures excluded'),
                       Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label='failures counted as 1')],
              loc='upper right', fontsize=9)
    a2.set_title('Effective quality')
    head(fig, f'{RQ_TITLE[rq]} — reliability vs. quality')
    save(fig, f'fig04_failures_effective_quality_{rq.lower()}')

# Original notebook cell 12
# Figure 5 — is quality project-dependent? model x repo heatmap of overall quality
REPO_LABEL = {'project-a': 'project-a', 'project-d': 'project-d', 'project-e': 'project-e',
              'project-f': 'project-f', 'project-b': 'project-b', 'project-c': 'project-c'}
for rq, d in rq_frames():
    piv = d.pivot_table(index='model', columns='repo', values='Overall', aggfunc='mean',
                        observed=True).reindex(MODEL_ORDER)
    piv.columns = [REPO_LABEL.get(c, c) for c in piv.columns]
    fig, ax = plt.subplots(figsize=(8.4, .55 * len(MODEL_ORDER) + 1.2))
    im = ax.imshow(piv.values, cmap=SEQ, vmin=1, vmax=5, aspect='auto')
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f'{v:.1f}', ha='center', va='center', fontsize=9.5,
                        color='white' if v > 3.2 else INK)
    ax.set_xticks(range(piv.shape[1]), piv.columns, rotation=20, ha='right')
    ax.set_yticks(range(piv.shape[0]), piv.index); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=.03, pad=.02); cb.outline.set_visible(False)
    cb.set_label('Overall quality (1–5)', color=INK_2, fontsize=9)
    ax.set_title(f'{RQ_TITLE[rq]} — quality per project')
    save(fig, f'fig05_quality_by_repo_{rq.lower()}')

# Original notebook cell 13
# Figure 6 — agentic (tool-calling) vs. single-shot prompting. Balanced by design.
for rq, d in rq_frames():
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    w, x = .38, np.arange(NM)
    for k, (flag, alpha, hatch, lbl) in enumerate([(False, 1.0, None, 'direct prompt'),
                                                   (True, .42, '//', 'tool-calling')]):
        vals = [d[(d.model == m) & (d.tool_calling == flag)]['Overall'].mean() for m in MODEL_ORDER]
        errs = [ci95(d[(d.model == m) & (d.tool_calling == flag)]['Overall']) for m in MODEL_ORDER]
        b = ax.bar(x + (k - .5) * w, vals, w * .9, yerr=errs, capsize=3,
                   color=[MODEL_COLOR[m] for m in MODEL_ORDER], alpha=alpha, hatch=hatch,
                   edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
        barlabels(ax, b, dy=.12)
    ax.set_xticks(x, MODEL_TICKS)
    ax.set_ylim(1, 5.4); ax.set_yticks(range(1, 6)); ax.set_ylabel('Overall quality (1–5)'); ygrid(ax)
    ax.legend(handles=[Patch(facecolor=MUTED, label='direct prompt'),
                       Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label='tool-calling')],
              ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
    ax.set_title(f'{RQ_TITLE[rq]} — does agentic tool-calling help?')
    ax.text(0, 1.02, 'bars are 95% CI', transform=ax.transAxes, color=MUTED, fontsize=8.5)
    save(fig, f'fig06_tool_calling_{rq.lower()}')
    for m in MODEL_ORDER:
        a = d[(d.model == m) & ~d.tool_calling]['Overall'].dropna()
        b_ = d[(d.model == m) & d.tool_calling]['Overall'].dropna()
        if len(a) > 1 and len(b_) > 1:
            print(f'{rq} {m}: Mann–Whitney {pstar(stats.mannwhitneyu(a, b_).pvalue)}')

# Original notebook cell 14
# Figure 7 (RQ1 only) — generating a README from scratch vs. updating an existing one.
# Caveat: generation has only 4-12 valid contexts per model. Reported, not concluded from.
d = ctxv[ctxv.rq == 'RQ1']
fig, ax = plt.subplots(figsize=(7.8, 4.3))
w, x = .38, np.arange(NM)
for k, (t, alpha, hatch) in enumerate([('README (generation)', 1.0, None), ('README (update)', .42, '//')]):
    sub = [d[(d.model == m) & (d.task == t)]['Overall'] for m in MODEL_ORDER]
    b = ax.bar(x + (k - .5) * w, [s.mean() for s in sub], w * .9,
               yerr=[ci95(s) for s in sub], capsize=3, color=[MODEL_COLOR[m] for m in MODEL_ORDER],
               alpha=alpha, hatch=hatch, edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
    barlabels(ax, b, dy=.12)
    for xi, s in zip(x + (k - .5) * w, sub):
        ax.text(xi, 1.06, f'n={s.notna().sum()}', ha='center', fontsize=7.5, color=MUTED)
ax.set_xticks(x, MODEL_TICKS)
ax.set_ylim(1, 5.4); ax.set_yticks(range(1, 6)); ax.set_ylabel('Overall quality (1–5)'); ygrid(ax)
ax.legend(handles=[Patch(facecolor=MUTED, label='README generation'),
                   Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label='README update')],
          ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
ax.set_title('RQ1 — generating vs. updating a README')
ax.text(0, 1.02, 'bars are 95% CI · generation has few valid contexts per model (see n)',
        transform=ax.transAxes, color=MUTED, fontsize=8.5)
save(fig, 'fig07_generation_vs_update_rq1')

# Original notebook cell 15
# Figure 8 (RQ2 only) — do mixed commits (several concerns in one commit) hurt the CHANGELOG?
d = ctxv[(ctxv.rq == 'RQ2') & ctxv.commit_mixed.notna()]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw=dict(width_ratios=[1.3, 1]))
w, x = .38, np.arange(NM)
for k, (flag, alpha, hatch) in enumerate([(False, 1.0, None), (True, .42, '//')]):
    sub = [d[(d.model == m) & (d.commit_mixed == flag)]['Overall'] for m in MODEL_ORDER]
    b = axes[0].bar(x + (k - .5) * w, [s.mean() for s in sub], w * .9, yerr=[ci95(s) for s in sub],
                    capsize=3, color=[MODEL_COLOR[m] for m in MODEL_ORDER], alpha=alpha,
                    hatch=hatch, edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
    barlabels(axes[0], b, dy=.12)
axes[0].set_xticks(x, MODEL_TICKS)
axes[0].set_ylim(1, 5.4); axes[0].set_yticks(range(1, 6)); axes[0].set_ylabel('Overall quality (1–5)')
ygrid(axes[0]); axes[0].set_title('Per model')
axes[0].legend(handles=[Patch(facecolor=MUTED, label='single-concern commit'),
                        Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label='mixed commit')],
               ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
for k, dim in enumerate(DIM_EN):
    for j, flag in enumerate([False, True]):
        s = d[d.commit_mixed == flag][dim]
        axes[1].bar(k + (j - .5) * .38, s.mean(), .34, yerr=ci95(s), capsize=3,
                    color=MODEL_COLOR[MODEL_ORDER[0]], alpha=1.0 if not flag else .42,
                    hatch=None if not flag else '//', edgecolor=SURFACE, error_kw=dict(ecolor=INK_2, lw=1))
axes[1].set_xticks(range(4), [d_[:6] + '.' for d_ in DIM_EN]); axes[1].set_ylim(1, 5)
axes[1].set_yticks(range(1, 6)); ygrid(axes[1]); axes[1].set_title('Pooled, per criterion')
a = d[~d.commit_mixed]['Overall'].dropna(); b_ = d[d.commit_mixed]['Overall'].dropna()
head(fig, 'RQ2 — effect of mixed commits on CHANGELOG quality',
     f'n = {len(a)} single-concern vs {len(b_)} mixed · Mann–Whitney {pstar(stats.mannwhitneyu(a, b_).pvalue)}')
save(fig, 'fig08_mixed_commits_rq2')

# Original notebook cell 16
# Figure 9 — inter-annotator agreement (validity of every accuracy figure above).
import krippendorff
rows = []
for dim in DIM_EN:
    # two raters per context, but the *pair* differs across contexts -> slot 0/1 per context
    w = annv.assign(slot=annv.groupby('uid').cumcount()).pivot_table(index='uid', columns='slot', values=dim)
    w = w.dropna()
    a, b = w[0], w[1]
    alpha = krippendorff.alpha(reliability_data=[a.values, b.values], level_of_measurement='ordinal')
    rows.append(dict(dim=dim, n=len(w), exact=(a == b).mean(), within1=(abs(a - b) <= 1).mean(),
                     alpha=alpha, r=stats.spearmanr(a, b).statistic))
agree = pd.DataFrame(rows)
display(agree.round(3))

fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw=dict(width_ratios=[1.35, 1]))
x, w = np.arange(4), .38
b1 = a1.bar(x - w/2, agree['exact'] * 100, w*.9, color='#2a78d6', label='exact match')
b2 = a1.bar(x + w/2, agree['within1'] * 100, w*.9, color='#2a78d6', alpha=.42,
            hatch='//', edgecolor=SURFACE, label='within ±1 point')
barlabels(a1, list(b1) + list(b2), fmt='{:.0f}%', dy=1.2)
a1.set_xticks(x, agree['dim']); a1.set_ylim(0, 100); a1.set_ylabel('Agreement between the 2 annotators (%)')
ygrid(a1); a1.legend(loc='upper left', fontsize=9); a1.set_title('Rater agreement')
bars = a2.bar(x, agree['alpha'], .55, color='#2a78d6')
barlabels(a2, bars, dy=.01)
a2.axhline(.667, color=ST_CRITICAL, ls='--', lw=1.2)
a2.text(3.45, .68, 'α = .667\n(tentative)', fontsize=8, color=ST_CRITICAL, ha='right')
a2.set_xticks(x, agree['dim']); a2.set_ylim(0, 1)
a2.set_ylabel("Krippendorff's α (ordinal)"); ygrid(a2); a2.set_title('Reliability')
head(fig, 'Inter-annotator agreement across both RQs',
     f'n = {agree["n"].iloc[0]} contexts rated twice · ratings averaged for all other figures')
save(fig, 'fig09_inter_annotator_agreement')

# Original notebook cell 17
# Figure 10 — are the four criteria measuring four different things?
for rq, d in rq_frames():
    corr = d[DIM_EN].corr(method='spearman')
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    im = ax.imshow(corr.values, cmap=SEQ, vmin=0, vmax=1)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f'{corr.values[i, j]:.2f}', ha='center', va='center', fontsize=10,
                    color='white' if corr.values[i, j] > .62 else INK)
    ax.set_xticks(range(4), [d_[:6] + '.' for d_ in DIM_EN])
    ax.set_yticks(range(4), DIM_EN); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=.045, pad=.03); cb.outline.set_visible(False)
    cb.set_label("Spearman ρ", color=INK_2, fontsize=9)
    ax.set_title(f'{RQ_TITLE[rq]} — criteria correlation')
    save(fig, f'fig10_criteria_correlation_{rq.lower()}')

# Original notebook cell 19
# Figure 11 — token consumption per model (log scale: the models differ by ~5x)
for rq, d in rq_frames():
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    cols = [('input_tokens', 'input', 1.0, None), ('output_tokens', 'output', .42, '//'),
            ('total_tokens', 'total', .18, 'xx')]
    x, w = np.arange(NM), .26
    for k, (c, lbl, alpha, hatch) in enumerate(cols):
        vals = [d[d.model == m][c].mean() for m in MODEL_ORDER]
        b = ax.bar(x + (k - 1) * w, vals, w * .9, color=[MODEL_COLOR[m] for m in MODEL_ORDER],
                   alpha=alpha, hatch=hatch, edgecolor=SURFACE)
        for bb, v in zip(b, vals):
            if np.isfinite(v):
                ax.text(bb.get_x() + bb.get_width()/2, v * 1.08, f'{v:,.0f}', ha='center',
                        fontsize=7.5, color=INK_2, rotation=90)
    ax.set_yscale('log'); ax.set_ylim(10, 1e5)
    ax.set_xticks(x, MODEL_TICKS)
    ax.set_ylabel('Tokens per run (mean, log scale)'); ygrid(ax)
    ax.legend(handles=[Patch(facecolor=MUTED, label='input'),
                       Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label='output'),
                       Patch(facecolor=MUTED, alpha=.18, hatch='xx', edgecolor=SURFACE, label='total')],
              ncol=3, loc='upper center', bbox_to_anchor=(.5, -.12))
    ax.set_title(f'{RQ_TITLE[rq]} — token consumption')
    save(fig, f'fig11_tokens_{rq.lower()}')
    display(d.groupby('model', observed=True)[['input_tokens', 'output_tokens', 'total_tokens']].mean().round(0))

# Original notebook cell 20
# Figure 12 — response time distribution per model, one panel per task
for rq, _ in rq_frames():
    tasks = [t for t in TASK_ORDER if TASK_RQ[t] == rq]
    fig, axes = plt.subplots(1, len(tasks), figsize=(5.6 * len(tasks), 4.3), sharey=True, squeeze=False)
    for ax, t in zip(axes[0], tasks):
        d = ctxv[ctxv.task == t]
        data = [d[d.model == m]['runtime_s'].dropna().values for m in MODEL_ORDER]
        bp = ax.boxplot(data, patch_artist=True, widths=.55, showfliers=False,
                        medianprops=dict(color=INK, lw=2), whiskerprops=dict(color=AXIS),
                        capprops=dict(color=AXIS), boxprops=dict(edgecolor=SURFACE, lw=2))
        for patch, m in zip(bp['boxes'], MODEL_ORDER):
            patch.set_facecolor(MODEL_COLOR[m]); patch.set_alpha(.55)
        for i, v in enumerate(data, start=1):
            if len(v):
                ax.text(i, np.percentile(v, 75), f'{np.median(v):.0f}s median', ha='center',
                        va='bottom', fontsize=8, color=INK_2)
        ax.set_xticks(range(1, NM + 1), MODEL_TICKS, fontsize=8.5)
        ax.set_title(t); ygrid(ax)
    axes[0][0].set_ylabel('Response time per run (s)')
    head(fig, f'{RQ_TITLE[rq]} — response time',
         'box = IQR, line = median, whiskers = 1.5·IQR (outliers hidden)')
    save(fig, f'fig12_response_time_{rq.lower()}')

# Original notebook cell 21
# Figures 13 & 14 — the cost/benefit frontier: quality against time, and quality against tokens.
def frontier(ax, pts):
    # Pareto set for (minimise x, maximise y): keep a point only if nothing cheaper is better
    best, keep = -np.inf, []
    for xx, yy in sorted(pts):
        if yy > best:
            keep.append((xx, yy)); best = yy
    # only worth drawing when there are enough points for a frontier to mean something
    if len(pts) >= 6 and len(keep) > 1:
        ax.step(*zip(*keep), where='post', color=AXIS, lw=1.4, ls='--', zorder=0)

MARKERS = ['o', 's', '^', 'D', 'P']       # secondary encoding: shape backs up hue
TASK_SHORT = {'README (generation)': 'gen', 'README (update)': 'upd', 'CHANGELOG': 'chg'}
for xcol, xlabel, logx, fname, num in [('runtime_s', 'Mean response time per run (s)', False, 'fig13_quality_vs_time', 13),
                                       ('total_tokens', 'Mean total tokens per run', True, 'fig14_quality_vs_tokens', 14)]:
    for rq, d in rq_frames():
        agg = (d.groupby(['model', 'task'], observed=True)
                 .agg(q=('Overall', 'mean'), x=(xcol, 'mean'), tok=('total_tokens', 'mean'), n=('uid', 'size'))
                 .reset_index().dropna(subset=['x', 'q']))
        fig, ax = plt.subplots(figsize=(7.6, 4.8))
        for i, m in enumerate(MODEL_ORDER):
            g = agg[agg.model == m]
            ax.scatter(g['x'], g['q'], s=np.clip(g['tok'] / agg['tok'].max() * 480, 60, 520),
                       color=MODEL_COLOR[m], marker=MARKERS[i], alpha=.8,
                       edgecolor=SURFACE, linewidth=2, zorder=3, label=m)
            if agg['task'].nunique() > 1:        # pointless when the RQ has a single task
                for _, r in g.iterrows():
                    ax.annotate(TASK_SHORT[r['task']], (r['x'], r['q']), textcoords='offset points',
                                xytext=(11, 5), fontsize=7.5, color=MUTED)
        frontier(ax, [(r['x'], r['q']) for _, r in agg.iterrows()])
        if logx:
            ax.set_xscale('log')
        ax.set_xlabel(xlabel); ax.set_ylabel('Overall quality (1–5)')
        ax.set_ylim(1, 5); ax.set_yticks(range(1, 6)); ax.grid(True, which='major'); ax.set_axisbelow(True)
        # proxy handles: the real marks are size-encoded, which would blow up the legend
        ax.legend(handles=[mpl.lines.Line2D([], [], color=MODEL_COLOR[m], marker=MARKERS[i], ls='',
                                            markersize=9, label=m) for i, m in enumerate(MODEL_ORDER)],
                  ncol=1, loc='lower right', fontsize=9)
        ax.set_title(f'{RQ_TITLE[rq]} — quality vs. {"time" if not logx else "tokens"}')
        ax.text(0, 1.02, 'one point per model × task · bubble area = mean total tokens · up-and-left is better',
                transform=ax.transAxes, color=MUTED, fontsize=8.5)
        save(fig, f'{fname}_{rq.lower()}')

# Original notebook cell 22
# Figure 15 — money. API billing for Gemini, GPU-seconds for the self-hosted models.
# GPU_HOURLY: replace with the real hourly cost of the machine the Ollama models ran on.
GPU_HOURLY = 0.35     # USD/h -- e.g. a mid-range cloud GPU; edit before publishing
for rq, d in rq_frames():
    g = d.groupby('model', observed=True).agg(api=('total_cost', 'mean'), t=('runtime_s', 'mean')).reindex(MODEL_ORDER)
    g['proxy'] = np.where(g.index.isin(SELF_HOSTED), g['t'] / 3600 * GPU_HOURLY, 0)
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    x = np.arange(NM)
    b1 = ax.bar(x, g['api'] * 1000, .55, color=[MODEL_COLOR[m] for m in MODEL_ORDER], label='API billing')
    b2 = ax.bar(x, g['proxy'] * 1000, .55, bottom=g['api'] * 1000,
                color=[MODEL_COLOR[m] for m in MODEL_ORDER], alpha=.35, hatch='//', edgecolor=SURFACE)
    for xi, (_, r) in zip(x, g.iterrows()):
        tot = (r['api'] + r['proxy']) * 1000
        lab = (f"${r['proxy']*1000:.2f} compute" if r.name in SELF_HOSTED
               else f"${r['api']*1000:.2f} API")
        ax.text(xi, tot + .15, lab, ha='center', fontsize=8.5, color=INK_2)
    ax.set_xticks(x, MODEL_TICKS)
    ax.set_ylim(0, ((g['api'] + g['proxy']) * 1000).max() * 1.18)
    ax.set_ylabel('USD per 1 000 runs'); ygrid(ax)
    ax.legend(handles=[Patch(facecolor=MUTED, label='API billing (metered)'),
                       Patch(facecolor=MUTED, alpha=.35, hatch='//', edgecolor=SURFACE,
                             label=f'self-hosted GPU time proxy (@ ${GPU_HOURLY:.2f}/h)')],
              ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
    ax.set_title(f'{RQ_TITLE[rq]} — cost per 1 000 runs')
    ax.text(0, 1.02, 'self-hosted models are billed $0 by the provider; the hatched part is wall-clock GPU time, not free',
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    save(fig, f'fig15_cost_{rq.lower()}')

# Original notebook cell 23
# Figure 16 — how much context each project costs, and where the window runs out.
CTX_LIMIT = 32768
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw=dict(width_ratios=[1.5, 1]))
d = ctxv
order = d.groupby('repo')['input_tokens'].median().sort_values().index.tolist()
for i, m in enumerate(MODEL_ORDER):
    g = d[d.model == m]
    xs = [order.index(r) + (i - (NM - 1) / 2) * .2 for r in g['repo']]
    axes[0].scatter(xs, g['input_tokens'], s=26, color=MODEL_COLOR[m], marker=MARKERS[i],
                    alpha=.75, edgecolor=SURFACE, linewidth=.6, label=m)
axes[0].axhline(CTX_LIMIT, color=ST_CRITICAL, ls='--', lw=1.2)
axes[0].text(-.45, CTX_LIMIT * 1.25, f'context limit — {CTX_LIMIT:,} tokens', color=ST_CRITICAL,
             fontsize=8.5, ha='left')
axes[0].set_yscale('log'); axes[0].set_xticks(range(len(order)), [REPO_LABEL.get(r, r) for r in order],
                                              rotation=20, ha='right')
axes[0].set_ylabel('Input tokens per run (log)'); ygrid(axes[0]); axes[0].legend(ncol=2, fontsize=8.5)
axes[0].set_title('Input size per project')
capped = d[d.input_tokens >= CTX_LIMIT].groupby('model', observed=True).size().reindex(MODEL_ORDER).fillna(0)
tot = d.groupby('model', observed=True).size().reindex(MODEL_ORDER)
b = axes[1].bar(range(NM), capped / tot * 100, .55, color=[MODEL_COLOR[m] for m in MODEL_ORDER])
barlabels(axes[1], b, fmt='{:.1f}%', dy=.15)
axes[1].set_xticks(range(NM), MODEL_TICKS, fontsize=8.5)
axes[1].set_ylabel('Runs hitting the context limit (%)'); ygrid(axes[1])
axes[1].set_title('Truncated inputs')
head(fig, 'Context pressure across both RQs')
save(fig, 'fig16_context_pressure')

# Original notebook cell 24
# Figure 17 — agentic overhead: number of LLM calls (observations) per run
for rq, d in rq_frames():
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    x, w = np.arange(NM), .38
    for k, (flag, alpha, hatch, lbl) in enumerate([(False, 1.0, None, 'direct prompt'),
                                                   (True, .42, '//', 'tool-calling')]):
        vals = [d[(d.model == m) & (d.tool_calling == flag)]['num_observations'].mean() for m in MODEL_ORDER]
        b = ax.bar(x + (k - .5) * w, vals, w * .9, color=[MODEL_COLOR[m] for m in MODEL_ORDER],
                   alpha=alpha, hatch=hatch, edgecolor=SURFACE)
        barlabels(ax, b, fmt='{:.1f}', dy=.15)
    ax.set_xticks(x, MODEL_TICKS)
    ax.set_ylabel('LLM calls per run (mean)'); ygrid(ax)
    ax.legend(handles=[Patch(facecolor=MUTED, label='direct prompt'),
                       Patch(facecolor=MUTED, alpha=.42, hatch='//', edgecolor=SURFACE, label='tool-calling')],
              ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
    ax.set_title(f'{RQ_TITLE[rq]} — calls per run')
    save(fig, f'fig17_observations_{rq.lower()}')

# Original notebook cell 25
# Figure 18 — where local inference time actually goes (Ollama traces only).
d = ctxv.dropna(subset=['total_duration_s'])
if len(d):
    parts = [('load_duration_s', 'model load', 1.0, None),
             ('prompt_eval_duration_s', 'prompt eval', .55, '//'),
             ('eval_duration_s', 'generation', .25, 'xx')]
    g = d.groupby('model', observed=True)[[p[0] for p in parts]].mean().reindex(MODEL_ORDER).dropna(how='all')
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    bottom = np.zeros(len(g))
    for c, lbl, alpha, hatch in parts:
        v = g[c].fillna(0).values
        ax.bar(range(len(g)), v, .55, bottom=bottom, color=[MODEL_COLOR[m] for m in g.index],
               alpha=alpha, hatch=hatch, edgecolor=SURFACE, linewidth=2)
        bottom += v
    for i, tot in enumerate(bottom):
        ax.text(i, tot + .3, f'{tot:.1f}s', ha='center', fontsize=8.5, color=INK_2)
    ax.set_xticks(range(len(g)), [MODEL_SHORT[m] for m in g.index])
    ax.set_ylabel('Seconds per run (mean)'); ygrid(ax)
    ax.legend(handles=[Patch(facecolor=MUTED, alpha=a, hatch=h, edgecolor=SURFACE, label=l)
                       for _, l, a, h in parts], ncol=3, loc='upper center', bbox_to_anchor=(.5, -.12))
    ax.set_title('Self-hosted inference time breakdown')
    ax.text(0, 1.02, f'n = {len(d)} runs with Ollama timing fields (both RQs pooled)',
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    save(fig, 'fig18_ollama_time_breakdown')

# Original notebook cell 27
# 3.1 — build the coding corpus (run once, then code by hand)
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
    'verbose_repeated': ['repet', 'verboso', 'prolixo', 'muito longo', 'extenso', 'duplicad', 'redundan'],
    'too_generic':      ['genéric', 'generic', 'vago', 'superficial', 'raso', 'óbvio', 'obvio', 'não detalha'],
    'truncated':        ['truncad', 'cortad', 'interromp', 'incompleta no final', 'pela metade'],
    'confusing':        ['confus', 'não faz sentido', 'nao faz sentido', 'difícil de entender', 'não entendi',
                         'não ficou claro', 'nao ficou claro', 'ilegível'],
    'wrong_language':   ['inglês', 'ingles', 'português', 'portugues', 'idioma', 'traduz'],
    'meta_leakage':     ['prompt', 'instrução', 'instrucao', 'meta', 'explicação do modelo', 'comentário do modelo'],
    'irrelevant':       ['irrelevante', 'não relevante', 'fora de contexto', 'nada a ver', 'não tem relação'],
}

def seed_codes(txt):
    t = str(txt).lower()
    hits = [c for c, kws in CODEBOOK.items() if any(k in t for k in kws)]
    return ';'.join(hits) if hits else 'uncoded'

rows = []
for dim in DIM_EN:
    sub = annv[(annv[dim] <= 2) & annv['cmt_' + dim].notna()]
    for _, r in sub.iterrows():
        rows.append(dict(uid=r.uid, repo=r.repo, context_id=r.context_id, user_id=r.user_id,
                         rq=r.rq, task=r.task, model=r.model, tool_calling=r.tool_calling,
                         criterion=dim, score=r[dim], comment=str(r['cmt_' + dim]).strip()))
low = pd.DataFrame(rows)
low['code_auto'] = low['comment'].map(seed_codes)
low['code_final'] = ''
low.to_csv('low_score_comments_TO_CODE.csv', index=False)

print(f'{len(low)} low-score comments exported to low_score_comments_TO_CODE.csv')
print(f'seed rules matched {(low.code_auto != "uncoded").mean():.0%} of them\n')
display(low.groupby(['rq', 'criterion']).size().unstack(fill_value=0))
display(low['code_auto'].str.split(';').explode().value_counts().to_frame('seed hits'))

# Original notebook cell 28
# 3.2 — load the coded file (falls back to the automatic seeds if you have not coded yet)
CODED = os.path.join(DATA_DIR, 'low_score_comments_CODED.csv')
if os.path.exists(CODED):
    low = pd.read_csv(CODED)
    src = 'code_final'
    print('using MANUAL codes from', CODED)
else:
    src = 'code_auto'
    print('!! no coded file found — figures 19–23 use the KEYWORD SEEDS.')
    print('   Code low_score_comments_TO_CODE.csv by hand and save it as', CODED)

low['codes'] = low[src].fillna('').replace('', 'uncoded').astype(str)
lc = low.assign(code=low['codes'].str.split(';')).explode('code').reset_index(drop=True)
lc['code'] = lc['code'].str.strip()
lc = lc[lc.code.ne('')]
CODE_ORDER = lc['code'].value_counts().index.tolist()
CODE_LABEL = {c: c.replace('_', ' ') for c in CODE_ORDER}
# figures 20-23 describe the *composition* of the coded comments, so 'uncoded' is dropped there;
# figure 19 keeps it, because how much is still uncoded is itself worth seeing
lcc = lc[lc.code != 'uncoded'].copy()
print(len(lc), 'comment-code pairs across', lc.code.nunique(), 'codes;',
      f'{lc.code.eq("uncoded").mean():.0%} still uncoded')

# Original notebook cell 29
# Figure 19 — what annotators complain about, per RQ
for rq in ('RQ1', 'RQ2'):
    d = lc[lc.rq == rq]
    cnt = d['code'].value_counts()
    fig, ax = plt.subplots(figsize=(8, .42 * len(cnt) + 1.8))
    y = np.arange(len(cnt))[::-1]
    # 'uncoded' is not a finding -- grey it out so it never reads as a category
    b = ax.barh(y, cnt.values, .62, color=[MUTED if c == 'uncoded' else '#2a78d6' for c in cnt.index])
    n_com = d['comment'].nunique()
    for yy, v in zip(y, cnt.values):
        ax.text(v + max(cnt) * .012, yy, f'{v}  ({v/n_com:.0%})', va='center', fontsize=8.5, color=INK_2)
    ax.set_yticks(y, [CODE_LABEL.get(c, c) for c in cnt.index])
    ax.set_xlim(0, max(cnt) * 1.18); ax.set_xlabel('Comments carrying the code'); xgrid(ax)
    ax.set_title(f'{RQ_TITLE[rq]} — reasons behind low ratings')
    ax.text(0, 1.02 if len(cnt) > 6 else 1.06, f'{n_com} comments on ratings ≤ 2 · a comment may carry several codes',
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    save(fig, f'fig19_low_score_codes_{rq.lower()}')

# Original notebook cell 30
# Figure 20 — which model fails in which way
TOP = 8
for rq in ('RQ1', 'RQ2'):
    d = lcc[lcc.rq == rq]
    keep = d['code'].value_counts().head(TOP).index.tolist()
    ct = (pd.crosstab(d[d.code.isin(keep)]['model'], d[d.code.isin(keep)]['code'], normalize='index') * 100)
    ct = ct.reindex(index=[m for m in MODEL_ORDER if m in ct.index], columns=keep)
    steps = CAT8[:len(keep)]          # codes are nominal -> categorical hues, not a ramp
    fig, ax = plt.subplots(figsize=(10, .8 * len(ct) + 2.4))
    left = np.zeros(len(ct))
    for c, col in zip(keep, steps):
        v = ct[c].fillna(0).values
        ax.barh(range(len(ct)), v, left=left, height=.6, color=col, edgecolor=SURFACE, linewidth=2)
        for yy, (val, l) in enumerate(zip(v, left)):
            if val >= 8:
                ax.text(l + val / 2, yy, f'{val:.0f}', ha='center', va='center',
                        fontsize=8, color=ink_on(col))
        left += v
    ax.set_yticks(range(len(ct)), ct.index); ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
    ax.grid(False); ax.set_xlabel('Share of that model’s low-score codes')
    ax.legend(handles=[Patch(facecolor=col, label=CODE_LABEL.get(c, c)) for c, col in zip(keep, steps)],
              ncol=3, loc='upper center', bbox_to_anchor=(.5, -.16), fontsize=8.5)
    ax.set_title(f'{RQ_TITLE[rq]} — failure profile per model')
    save(fig, f'fig20_codes_by_model_{rq.lower()}')

# Original notebook cell 31
# Figure 21 — which criterion surfaces which complaint
for rq in ('RQ1', 'RQ2'):
    d = lcc[lcc.rq == rq]
    keep = d['code'].value_counts().head(TOP).index.tolist()
    piv = pd.crosstab(d[d.code.isin(keep)]['code'], d[d.code.isin(keep)]['criterion']).reindex(
        index=keep, columns=DIM_EN).fillna(0)
    fig, ax = plt.subplots(figsize=(6.6, .48 * len(piv) + 2))
    im = ax.imshow(piv.values, cmap=SEQ, aspect='auto')
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f'{v:.0f}', ha='center', va='center', fontsize=9,
                    color='white' if v > piv.values.max() * .55 else INK)
    ax.set_xticks(range(4), [c[:6] + '.' for c in DIM_EN])
    ax.set_yticks(range(len(piv)), [CODE_LABEL.get(c, c) for c in piv.index]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.03); cb.outline.set_visible(False)
    cb.set_label('Comments', color=INK_2, fontsize=9)
    ax.set_title(f'{RQ_TITLE[rq]} — code × criterion')
    save(fig, f'fig21_code_by_criterion_{rq.lower()}')

# Original notebook cell 32
# Figure 22 — do README failures differ from CHANGELOG failures? (diverging, shared axis)
p1 = lcc[lcc.rq == 'RQ1'].groupby('code')['comment'].nunique()
p2 = lcc[lcc.rq == 'RQ2'].groupby('code')['comment'].nunique()
n1, n2 = lc[lc.rq == 'RQ1']['comment'].nunique(), lc[lc.rq == 'RQ2']['comment'].nunique()
cmp = pd.DataFrame({'RQ1': p1 / n1 * 100, 'RQ2': p2 / n2 * 100}).fillna(0)
cmp = cmp.loc[(cmp.max(axis=1)).sort_values().index]

fig, ax = plt.subplots(figsize=(9, .44 * len(cmp) + 2))
y = np.arange(len(cmp))
ax.barh(y, -cmp['RQ1'], .62, color='#2a78d6', label='RQ1 — README')
ax.barh(y,  cmp['RQ2'], .62, color='#eb6834', label='RQ2 — CHANGELOG')
for yy, (a, b_) in enumerate(zip(cmp['RQ1'], cmp['RQ2'])):
    if a > 0:
        ax.text(-a - 1.2, yy, f'{a:.0f}%', va='center', ha='right', fontsize=8.5, color=INK_2)
    if b_ > 0:
        ax.text(b_ + 1.2, yy, f'{b_:.0f}%', va='center', ha='left', fontsize=8.5, color=INK_2)
lim = max(cmp.max()) * 1.35
ax.set_xlim(-lim, lim); ax.set_yticks(y, [CODE_LABEL.get(c, c) for c in cmp.index])
ax.set_xticks(ax.get_xticks(), [f'{abs(t):.0f}%' for t in ax.get_xticks()])
ax.axvline(0, color=AXIS, lw=1); xgrid(ax)
ax.set_xlabel('Share of low-score comments carrying the code')
ax.legend(ncol=2, loc='upper center', bbox_to_anchor=(.5, -.13))
ax.set_title('README vs. CHANGELOG — do they fail differently?')
ax.text(0, 1.02, f'n = {n1} RQ1 comments vs {n2} RQ2 comments, each normalised within its RQ',
        transform=ax.transAxes, color=MUTED, fontsize=8.5)
save(fig, 'fig22_rq1_vs_rq2_codes')

# Original notebook cell 33
# Figure 23 — which complaints travel together (co-occurrence within one comment)
pairs = (lcc.groupby(['uid', 'criterion', 'user_id'])['code'].apply(lambda s: sorted(set(s))))
co = pd.DataFrame(0, index=CODE_ORDER, columns=CODE_ORDER, dtype=int)
for codes in pairs:
    for a, b_ in itertools.combinations(codes, 2):
        co.loc[a, b_] += 1; co.loc[b_, a] += 1
keep = [c for c in CODE_ORDER if c != 'uncoded'][:TOP]
co = co.loc[keep, keep]
mask = np.triu(np.ones_like(co.values, dtype=bool))
fig, ax = plt.subplots(figsize=(7.2, 6))
im = ax.imshow(np.where(mask, np.nan, co.values), cmap=SEQ)
for i in range(len(keep)):
    for j in range(len(keep)):
        if not mask[i, j] and co.values[i, j] > 0:
            ax.text(j, i, co.values[i, j], ha='center', va='center', fontsize=8.5,
                    color='white' if co.values[i, j] > co.values.max() * .55 else INK)
ax.set_xticks(range(len(keep)), [CODE_LABEL.get(c, c) for c in keep], rotation=35, ha='right')
ax.set_yticks(range(len(keep)), [CODE_LABEL.get(c, c) for c in keep]); ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=.045, pad=.03); cb.outline.set_visible(False)
cb.set_label('Comments carrying both codes', color=INK_2, fontsize=9)
ax.set_title('Code co-occurrence (both RQs)')
save(fig, 'fig23_code_cooccurrence')

# Original notebook cell 35
# 4.1 — one row per model x task: the whole story in a table
summary = (ctx.groupby(['rq', 'task', 'model'], observed=True)
             .agg(n=('uid', 'size'),
                  failed_pct=('failed', lambda s: 100 * s.mean()))
             .join(ctxv.groupby(['rq', 'task', 'model'], observed=True)
                     .agg(**{d: (d, 'mean') for d in DIM_EN},
                          overall=('Overall', 'mean'),
                          in_tok=('input_tokens', 'mean'), out_tok=('output_tokens', 'mean'),
                          tot_tok=('total_tokens', 'mean'), runtime_s=('runtime_s', 'mean'),
                          cost_usd=('total_cost', 'mean'), calls=('num_observations', 'mean')))
             .round(2))
display(summary)
summary.to_csv('figs/summary_by_model_task.csv')

overall_tbl = (ctx.groupby(['rq', 'model'], observed=True)
                 .agg(n=('uid', 'size'), failed_pct=('failed', lambda s: 100 * s.mean()))
                 .join(ctxv.groupby(['rq', 'model'], observed=True)
                         .agg(overall=('Overall', 'mean'), tot_tok=('total_tokens', 'mean'),
                              runtime_s=('runtime_s', 'mean'), cost_usd=('total_cost', 'mean')))
                 .round(2))
display(overall_tbl)
overall_tbl.to_csv('figs/summary_by_model.csv')
print('\nfigures written:'); print('\n'.join(sorted(os.listdir('figs'))))

# Additional machine-readable exports; no change to the analysis.
ann.to_csv('figs/annotations.csv', index=False)
ctx.to_csv('figs/contexts.csv', index=False)
agree.to_csv('figs/inter_annotator_agreement.csv', index=False)
tests = []
for rq, d in rq_frames():
    p, dunn = kruskal_by_model(d, 'Overall')
    tests.append({'rq': rq, 'kruskal_p': p})
    if dunn is not None:
        dunn.to_csv(f'figs/dunn_holm_{rq.lower()}.csv')
pd.DataFrame(tests).to_csv('figs/kruskal_tests.csv', index=False)
