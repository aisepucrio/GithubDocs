"""Curate the supplied merged exports without modifying the source directory.

Only maintainers need this script. Reproduction uses the committed curated data.
Identifiers are assigned in sorted order across all seven input files; no mapping
back to the source evaluator IDs is published. Numerical values and row order
are retained. Email/path masking preserves string lengths used by the analyses.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
from pathlib import Path

try:
    from .anonymize import Anonymizer
except ImportError:
    from anonymize import Anonymizer

csv.field_size_limit(sys.maxsize)
ROOT = Path(__file__).resolve().parents[1]
REPOS = (
    "project-a",
    "event_flow",
    "ngx_admin_lte",
    "pos_mamba_sdk",
    "project-b",
    "project-c",
)
FILES = [f"{repo}_answers_merged.csv" for repo in REPOS] + ["claude_code_answers.csv"]
# Operational identifiers and collector internals are not needed for analysis.
DROP = {
    "C : id",
    "C : trace_id",
    "C : sessionId",
    "C : tags",
    "C : public",
    "C : bookmarked",
    "C : environment",
    "C : _source_file",
    "C : name",
    "C : metadata_tags",
    "C : metadata_thread_id",
    "C : metadata_checkpoint_ns",
    "C : metadata_resourceAttributes",
    "C : metadata_langgraph_node",
    "C : metadata_langgraph_path",
    "C : metadata_langgraph_step",
    "C : metadata_langgraph_triggers",
}
MASKS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "home_path": re.compile(r"/(?:home|Users)/[^/\s\"']+"),
}
SECRET = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{25,}|"
    r"AIza[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,})"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--destination", type=Path, default=ROOT)
    parser.add_argument("--anonymization-map", type=Path, required=True)
    args = parser.parse_args()
    anonymizer = Anonymizer(args.anonymization_map)
    dest = args.destination
    loaded = {name: read_csv(args.source / anonymizer.sources[name]) for name in FILES}
    users = sorted({row["user_id"] for _, rows in loaded.values() for row in rows})
    human_users = [user for user in users if user not in ("-1", "-2")]
    user_map = {user: f"rater-{i:02d}" for i, user in enumerate(human_users, 1)}
    user_map.update({"-1": "synthetic-01", "-2": "synthetic-02"})
    manifest = {
        "schema_version": 2,
        "source_description": "Author-supplied merged exports and analysis notebooks",
        "human_rater_ids": len(human_users),
        "synthetic_rater_ids": 2,
        "redaction": (
            "Evaluator pseudonyms; operational identifiers removed; "
            "emails and home paths masked; internal project identities, URLs and "
            "revision hashes withheld. Original output lengths retained separately."
        ),
        "files": [],
        "analyses": ["rq1_rq2", "rq3"],
        "reference_tables": [],
        "expected_figures": sorted(
            str(path.relative_to(args.source))
            for dirname in ("figs", "figs_rq3")
            for path in (args.source / dirname).iterdir()
            if path.suffix in {".pdf", ".png"}
        ),
    }
    (dest / "data").mkdir(parents=True, exist_ok=True)
    experiments = []
    for name, (fields, rows) in loaded.items():
        fields = [field for field in fields if field not in DROP]
        fields.append("C : output_char_count")
        curated_rows = []
        counts = {label: 0 for label in MASKS}
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            clean = {}
            for field in fields:
                if field == "C : output_char_count":
                    clean[field] = len(row.get("C : output", "").strip())
                    continue
                value = user_map[row[field]] if field == "user_id" else row[field]
                if SECRET.search(value):
                    raise ValueError(
                        f"Possible credential in {name}, column {field}; "
                        "review before import"
                    )
                for label, pattern in MASKS.items():
                    value, count = pattern.subn(
                        lambda match: "x" * len(match[0]), value
                    )
                    counts[label] += count
                clean[field] = anonymizer.record(value)
            writer.writerow(clean)
            curated_rows.append(clean)
        target = dest / "data" / (name + ".gz")
        target.write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))
        manifest["files"].append({
            "path": str(target.relative_to(dest)),
            "dataset": name,
            "sha256": sha256(target),
            "rows": len(rows),
            "contexts": len({r["context_id"] for r in rows}),
            "synthetic_rows": sum(r["user_id"] in ("-1", "-2") for r in rows),
            "columns": fields,
            "dropped_columns": sorted(DROP.intersection(loaded[name][0])),
            "masked_occurrences": counts,
        })
        seen = set()
        for row in curated_rows:
            if row["context_id"] in seen:
                continue
            seen.add(row["context_id"])
            experiments.append({
                "source": target.name,
                "context_id": row["context_id"],
                "system": "Claude Code"
                if name == "claude_code_answers.csv"
                else "DOME",
                **{
                    key: row.get(column, "")
                    for key, column in {
                        "case": "C : metadata_config_index",
                        "repo_path": "C : metadata_repo_path",
                        "task": "C : metadata_test_type",
                        "model": "C : metadata_model_name",
                        "temperature": "C : metadata_temperature",
                        "tool_calling": "C : is_tool_calling",
                        "mixed_commits": "C : metadata_commit_mixed",
                        "timestamp": "C : timestamp",
                    }.items()
                },
                "experiment_commit": "",
                "experiment_branch": "",
            })
    (dest / "provenance").mkdir(parents=True, exist_ok=True)
    with (dest / "provenance/experiments.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(experiments[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(experiments)
    for dirname in ("figs", "figs_rq3"):
        for source in sorted((args.source / dirname).glob("*.csv")):
            target = dest / "reference" / dirname / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(anonymizer.names(source.read_text()))
            manifest["reference_tables"].append({
                "path": str(target.relative_to(dest)),
                "sha256": sha256(target),
            })
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        f"Imported {sum(len(rows) for _, rows in loaded.values())} rows; "
        f"{len(human_users)} human rater IDs and 2 synthetic placeholder IDs"
    )


if __name__ == "__main__":
    main()
