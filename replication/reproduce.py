"""Verify the curated inputs, reproduce all analyses, and compare reference tables."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

try:
    from .scripts.anonymize import audit_data_bytes
except ImportError:
    from scripts.anonymize import audit_data_bytes

ROOT = Path(__file__).resolve().parent


def verify_inputs(root=ROOT):
    manifest = json.loads((root / "manifest.json").read_text())
    for entry in manifest["files"] + manifest["reference_tables"]:
        path = root / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {entry['path']}")
        if path.name.endswith(".csv.gz"):
            audit_data_bytes(path.name, path.read_bytes())
    return manifest


def compare_tables(output, root=ROOT):
    import pandas as pd

    checked = []
    for reference in sorted((root / "reference").rglob("*.csv")):
        relative = reference.relative_to(root / "reference")
        actual = output / relative
        pd.testing.assert_frame_equal(
            pd.read_csv(reference),
            pd.read_csv(actual),
            check_dtype=False,
            check_exact=False,
            rtol=1e-9,
            atol=1e-12,
            obj=str(relative),
        )
        checked.append(str(relative))
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = verify_inputs()
    print(
        f"Verified {len(manifest['files'])} datasets and "
        f"{len(manifest['reference_tables'])} reference tables",
        flush=True,
    )
    if args.verify_only:
        return
    output = args.output.resolve()
    # A fresh destination prevents stale figures or reports from appearing successful.
    if output.exists() and any(output.iterdir()):
        parser.error("Output directory must be empty; choose a new --output path")
    if output == ROOT or ROOT.is_relative_to(output):
        parser.error("Output must not contain the replication package")
    output.mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ,
        DOME_DATA_DIR=str(ROOT / "data"),
        MPLBACKEND="Agg",
        MPLCONFIGDIR=str(output / ".matplotlib"),
        PYTHONHASHSEED="0",
    )
    started = time.monotonic()
    for analysis in ("rq1_rq2", "rq3"):
        print(f"Running {analysis} (log: {output / (analysis + '.log')})", flush=True)
        with (output / (analysis + ".log")).open("w") as log:
            subprocess.run(
                [sys.executable, str(ROOT / "analysis" / (analysis + ".py"))],
                cwd=output,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
    checked = compare_tables(output)
    produced = sorted(
        str(path.relative_to(output))
        for path in output.glob("fig*/*")
        if path.suffix in {".pdf", ".png"}
    )
    if produced != manifest["expected_figures"]:
        raise ValueError("Generated figure inventory differs from the source inventory")
    report = {
        "status": "passed",
        "manifest_sha256": hashlib.sha256(
            (ROOT / "manifest.json").read_bytes()
        ).hexdigest(),
        "lockfile_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "analysis_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "analysis").glob("*.py"))
        },
        "reference_tables_matched": checked,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in (
                "numpy",
                "pandas",
                "scipy",
                "matplotlib",
                "krippendorff",
                "scikit-posthocs",
                "statsmodels",
            )
        },
        "figures_png": len(list(output.glob("fig*/*.png"))),
        "figures_pdf": len(list(output.glob("fig*/*.pdf"))),
        "qualitative_coding": "automatic keyword seeds (no manual CODED file supplied)",
        "scope": (
            "Supplied notebooks and reference CSVs; "
            "manuscript correspondence not verified"
        ),
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"PASS: {len(checked)} reference tables match; "
        f"{report['figures_pdf']} PDF figures reproduced",
        flush=True,
    )


if __name__ == "__main__":
    main()
