# DOME replication package

This package reproduces the supplied RQ1/RQ2 notebooks (README and CHANGELOG
evaluation) and RQ3 notebook (comparison with Claude Code). It includes curated
inputs, executable analyses, dependency versions, provenance and reference tables.
No API keys, Langfuse account, Google Sheets access, GPU or subject-repository
checkout is needed to reproduce the analyses.

The submitted manuscript was not supplied with these files. Agreement with the
five original CSV tables is checked automatically; correspondence with the exact
tables and figure numbers in the submitted paper remains to be confirmed.

## Quick start

Install Python 3.13 and [uv](https://docs.astral.sh/uv/), then, from the repository
root (or the root of the source archive):

```bash
uv sync --project replication --frozen
uv run --project replication --frozen python replication/reproduce.py
```

Dependencies are downloaded during setup. After installation the analysis is
offline and can also be run directly:

```bash
replication/.venv/bin/python replication/reproduce.py --output /tmp/dome-results
```

On Windows use `replication\.venv\Scripts\python.exe`. Choose a new output
directory for each run; a nonempty destination is rejected to avoid stale results.
The default destination is `replication/results/`, which is not versioned.

Expected completion message:

```text
PASS: 5 reference tables match; 51 PDF figures reproduced
```

The run also produces 51 PNG figures, normalized annotation/context CSVs,
inter-annotator agreement, Kruskal–Wallis and Dunn–Holm results, paired Wilcoxon
results, qualitative coding worksheets, logs and `validation.json`. Errors or
numeric discrepancies return a nonzero exit status. The five reference tables
use `rtol=1e-9`, `atol=1e-12`; PDF byte equality is not expected because rendering
metadata and installed fonts can vary.

Tested on Linux x86-64 (Python 3.13.9) and Windows 11 (Python 3.13.5), in
isolated environments. Figure generation
took approximately 18 seconds after dependency installation on the preparation
machine; allow several minutes on other machines. No GPU is used. Reserve about
1 GB of disk space for the environment and generated files. Other operating
systems have not been tested.

## Contents

| Location | Contents |
|---|---|
| `data/*.csv.gz` | Seven curated exports; gzip is read directly by pandas |
| `analysis/rq1_rq2.py` | Adaptation of the supplied RQ1/RQ2 notebook |
| `analysis/rq3.py` | Adaptation of the supplied RQ3 notebook |
| `reference/` | Five original CSV outputs, copied without numerical changes |
| `manifest.json` | Curated input/reference hashes, row counts and curation details |
| `provenance/experiments.csv` | 594 contexts with available task/model/configuration metadata |
| `provenance/repositories.csv` | Anonymous subject-project identifiers |
| `pyproject.toml`, `uv.lock` | Analysis environment, separate from framework dependencies |
| `docs/methodology.md` | Analysis definitions, figure mapping and limitations |
| `docs/reexecution.md` | Framework execution and missing historical configuration |
| `docs/release.md` | Anonymous review, licensing and preservation preparation |

## Data and validation

There are six DOME projects, five model labels, 540 DOME contexts and 54 Claude
Code contexts. Each context has two rows: 1,188 rows in total. Of these, 134 are
synthetic failure placeholders from the supplied exports, rather than human
judgments. Fourteen human evaluator identifiers were replaced with consistent
pseudonyms. The two synthetic identifiers are labeled separately.

```bash
python replication/reproduce.py --verify-only
uv run --project replication --frozen python -m unittest discover -s replication/tests -v
```

Checksums and the dataset privacy policy can be verified with Python's standard
library alone. The regression tests check data shape, pairing, privacy transformations and rejection of changed
reference results. Framework exporter tests are separate:

```bash
uv run --frozen python -m unittest discover -s tests -v
```

The qualitative figures currently use **automatic keyword seeds**. No manually
coded `*_CODED.csv` files were supplied. They must not be described as completed
manual thematic analysis. Model names are preserved as recorded by the supplied
exports/notebooks; immutable provider model versions were not independently
established.

## Maintainer import

Review the original material before importing another version. These commands
are not needed by reviewers and do not modify the source directory:

```bash
python replication/scripts/import_sources.py /path/to/merged \
  --anonymization-map /private/project-map.json
python replication/scripts/convert_notebooks.py \
  --rq12-notebook /private/rq12.ipynb --rq3-notebook /private/rq3.ipynb \
  --anonymization-map /private/project-map.json
```

The private map must be outside the repository. Its `sources` object maps each
public dataset filename to its original local filename; `patterns` contains
case-insensitive regular-expression/replacement pairs; `private_revisions` lists
additional revisions to withhold. The real mapping is not distributed.

Import preserves row order and numeric measurements, pseudonymizes evaluators,
removes collector identifiers, masks emails/home paths, and replaces subject
project names throughout the data. Embedded URLs and revision hashes are withheld,
as are personal names in commit trailers, notebook account metadata and citation
entries.
Original output lengths are recorded before redaction in `C : output_char_count`
and used by the analyses. Prompts and outputs are consequently deidentified
versions, not byte-identical original artifacts. Notebook execution outputs,
metadata, original filenames and original source hashes are not published.
The scripts retain source cell numbers. Re-run validation after any import or
code change. Subject projects appear only as `project-a` to `project-f`; their
repositories are not included as submodules.

Licensing and remaining publication steps are documented in
[the release guide](docs/release.md). No DOI or published artifact is claimed.
