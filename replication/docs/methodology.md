# Methodology and traceability

## Source material

The package was prepared from seven `*answers*.csv` files, two analysis notebooks
and five reference tables supplied together in a `merged` directory. SHA-256
values of the curated files are recorded in `manifest.json`; hashes and filenames
of identifiable originals are withheld. The source notebooks were
converted to Python with their code-cell numbers retained. Installation,
interactive upload, plotting display and download cells were replaced by local
file handling. Additional CSV exports expose the intermediate analysis tables.
No model calls are performed and no ratings or statistical methods were replaced.
Internal subject labels are anonymized in tables and figures. The original output
length is stored before text redaction and used for length-related measures.

The source exports are merged data, not the original collection system's full
audit trail. The transformation used to merge the original exports was not
supplied. Reproduction therefore starts at the merged annotation rows.

## Units and exclusions

- An annotation row is one evaluator/context pair with four 1–5 criteria:
  conciseness, correctness, completeness and clarity. Original Portuguese column
  names and comments are retained.
- A context is identified by repository and `context_id` (and system in RQ3).
  Each of the 594 contexts has two annotation rows. Ratings are averaged within
  contexts; the context is the main quantitative analysis unit.
- Eighteen individual criterion ratings are missing in the supplied DOME rows.
  They remain missing. Pandas means skip missing values, including when computing
  an annotation's overall score; this is the source notebook's behavior. Two
  annotation rows do not necessarily mean two available scores on every criterion.
- DOME has 540 contexts (90 per project); Claude Code has 54. RQ3 matches on the
  54 configuration/case indices. Direct and tool-calling DOME runs are compared
  separately or averaged by model/case, as in the source notebook.
- Fourteen human evaluator IDs occur in the exports. Source IDs `-1` and `-2`
  occur in 134 rows marked `is_filler=True`, all with score 1. They become
  `synthetic-01` and `synthetic-02`; they are not additional human participants.
- Failure detection uses filler markers, missing outputs and error messages.
  The supplied analyses classify 105 DOME contexts and 5 Claude Code contexts
  as failed. This exceeds the 67 contexts represented by synthetic placeholders.
- Conditional quality excludes failures. RQ3 effective quality replaces failure
  scores with 1. Figures and tables preserve the source notebook's denominators
  and distinguish conditional from effective scores.

## Statistics

Mean confidence intervals use Student's t distribution, not a bootstrap.
RQ1/RQ2 use Kruskal–Wallis with Dunn post-hoc comparisons and Holm adjustment,
and additional Mann–Whitney comparisons as shown in the source cells.
Inter-annotator agreement uses exact agreement, agreement within one point,
ordinal Krippendorff alpha and Spearman correlation. The notebook assigns the
two ratings to slots within each context; it does not estimate individual-rater
effects across the whole panel.

RQ3 uses paired Wilcoxon signed-rank tests and Cliff's delta. The source's
Wilcoxon p-values are not adjusted across its multiple comparisons. Cliff's
delta is calculated from cross-sample comparisons, even though the Wilcoxon
test is paired. The best-per-case configuration is an oracle ceiling using the
observed scores, not a deployable selection policy. These definitions are
preserved for faithful reproduction and should be considered when interpreting
the results.

Provider-billed cost is not total infrastructure cost: local inference and
hardware use are not made free by a zero API bill. Tokens, cache usage and
latency retain the definitions used in the source exports. RQ1/RQ2 use the
execution-time field; RQ3 uses the shared latency field. The RQ3 token consistency
check permits a relative residual below 0.001, as in the original notebook.

## Figure and table mapping

These are **notebook figure identifiers**, not confirmed manuscript numbers.

| Analysis cells | Output family | Purpose |
|---|---|---|
| RQ1/RQ2 8–17 | `figs/fig01_*` through `fig10_*` | Quality, reliability, task/configuration effects and agreement |
| RQ1/RQ2 19–25 | `figs/fig11_*` through `fig18_*` | Tokens, runtime, cost, context pressure and inference timing |
| RQ1/RQ2 27–33 | `figs/fig19_*` through `fig23_*` | Automatically seeded qualitative code distributions |
| RQ1/RQ2 35 | `figs/summary_by_model*.csv` | Two supplied reference tables |
| RQ3 8–14 | `figs_rq3/figR3_01_*` through `figR3_07_*` | Quality, pairing, oracle ceiling and rating distributions |
| RQ3 16, 18–20 | `figs_rq3/figR3_08_*` through `figR3_11_*` | Reliability, tokens, time and cost |
| RQ3 22–23 | `figs_rq3/figR3_12_*` | Automatically seeded qualitative comparison |
| RQ3 25 | `figs_rq3/rq3_*.csv` | Three supplied reference tables |

## Qualitative analysis

Low-score comments are assigned keyword-based seed codes. The source notebooks
look for `low_score_comments_CODED.csv` and `rq3_low_score_comments_CODED.csv`
but neither was supplied. The `TO_CODE` worksheets are generated anew from the
curated inputs. RQ1/RQ2 use low-score comments from valid runs; RQ3 uses all
annotation rows. Codebooks also differ slightly, as in the source notebooks.
Do not report these generated plots as validated manual coding or adjudication.

## Scope of the validation

Reproduction checks five CSV tables against independent, pre-existing reference
exports, including Wilcoxon p-values. It does not prove that the original study
design is valid or that every reference agrees with the submitted manuscript.
The original rubric, participant recruitment/consent procedure, exact model
snapshots, hardware specification, random seeds, historical framework commit
and per-case repository commits were not supplied in a verifiable manifest.
These are recorded as missing rather than inferred from the current checkout.
