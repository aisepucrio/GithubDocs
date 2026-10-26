# Reexecuting model experiments

Reproducing the analysis is fully supported by `../README.md`. Reexecuting the
historical model experiments requires additional information: the merged exports
do not identify all source commits, complete configurations or immutable model
snapshots. The current framework and prompts are available in the parent
repository, but their exact correspondence with the historical runs is unverified.

`../provenance/experiments.csv` records every context's available configuration
index, repository path, task, model label, temperature, tool-calling flag,
mixed-commit flag and timestamp. Blank experiment commit/branch fields mean
**unknown**. `../provenance/repositories.csv` lists the anonymous subject
identifiers. Subject project identities and Git references are intentionally
withheld for review, and their submodules are excluded. The maintainer's private
identity mapping is needed to locate those original checkouts for reexecution.

## Running the available framework

From a clone of the parent repository, with Python 3.13 and uv:

```bash
git submodule update --init --recursive
uv sync --frozen
mkdir -p output logs
uv run --frozen python main.py run conf/config_example.toml
```

This executes the checked-in example, not a reconstruction of all historical
experiments. Configure the selected provider credentials in the environment
before running it. Some providers require paid calls; local models require their
runtime and adequate hardware. The offline analysis command never invokes it.
Do not update submodules with `--remote` when trying to retain a pinned checkout.

For each confirmed historical case, record the repository HEAD, the exact
commit list being analyzed, branch, ignored files, prompt content/template,
model revision, temperature, seed if supported, context limits, strategy,
retry/timeout policy and provider/runtime version. Archive the full configuration
along with the run's output and errors. Do not substitute the example TOML for
these missing records.

The merged DOME exports retain rendered inputs in `C : input`, and the Claude
Code export retains `C : prompt`; both retain `C : output`. These are available
inside the gzip CSVs, including empty-output/failure records. These are
deidentified artifacts: subject project names, links and revisions are withheld,
and emails/home paths are masked. They help inspect the requests but are not a
complete environment snapshot or executable replacements for the original inputs.
Numeric measurements and pre-redaction output lengths are preserved separately.

The Claude Code notebook labels its baseline `Claude Code (Opus 5)`. The supplied
CSV does not independently establish an immutable model ID, CLI version, command
line, permissions or tool configuration. Obtain those from the experiment owner
before describing a new execution as an exact replication.

## Exporting future Langfuse runs

```bash
uv run --frozen python -m benchmark.export_results \
  --dataset-name DATASET_NAME --run-name RUN_NAME \
  --output-path output/langfuse_eval/results.csv
```

The output includes a compatibility CSV with the latest score per criterion,
a `.scores.csv` preserving all individual scores and a `.observations.jsonl`
preserving usage/cost details. Use the scores sidecar to define an explicit
policy for revisions and repeated raters. Missing measurements must remain
missing. This exporter is for future collection; it was not used to invent
or reconstruct absent fields in the historical study.
