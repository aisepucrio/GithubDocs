import gzip
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from replication.reproduce import compare_tables, verify_inputs
from replication.scripts.anonymize import (
    Anonymizer,
    audit_data_bytes,
    exposes_people,
    redact_people,
    validate_dataset,
)
from replication.scripts.build_archive import included
from replication.scripts.import_sources import MASKS, SECRET

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_checksums_and_experimental_design(self):
        manifest = verify_inputs()
        all_rows = []
        cases = {}
        for entry in manifest["files"]:
            frame = pd.read_csv(ROOT / entry["path"])
            self.assertEqual(len(frame), entry["rows"])
            self.assertEqual(frame.context_id.nunique(), entry["contexts"])
            self.assertTrue(frame.groupby("context_id").size().eq(2).all())
            self.assertTrue(frame.groupby("context_id").user_id.nunique().eq(2).all())
            for dimension in ("Clareza", "Completude", "Concisão", "Corretude"):
                scores = frame["Q : " + dimension]
                self.assertTrue((scores.isna() | scores.between(1, 5)).all())
            for _, row in frame.iterrows():
                key = row["C : metadata_config_index"]
                identity = (
                    row["C : metadata_repo_path"],
                    row["C : metadata_test_type"].split("/")[-1],
                )
                self.assertEqual(cases.setdefault(key, identity), identity)
            all_rows.append(frame)
        combined = pd.concat(all_rows)
        self.assertEqual(len(combined), 1188)
        self.assertEqual(
            combined[
                ["Q : " + d for d in ("Clareza", "Completude", "Concisão", "Corretude")]
            ]
            .isna()
            .sum()
            .sum(),
            18,
        )
        synthetic = combined.user_id.str.startswith("synthetic-")
        self.assertEqual(synthetic.sum(), 134)
        self.assertEqual(combined.loc[~synthetic, "user_id"].nunique(), 14)
        self.assertEqual(len(cases), 54)

    def test_curated_exports_do_not_expose_removed_identifiers(self):
        for path in (ROOT / "data").glob("*.csv.gz"):
            text = gzip.decompress(path.read_bytes()).decode()
            self.assertIsNone(SECRET.search(text))
            for pattern in MASKS.values():
                self.assertIsNone(pattern.search(text))
            frame = pd.read_csv(path)
            validate_dataset(frame, path.name)
            self.assertNotIn("C : trace_id", frame)
            self.assertNotIn("C : metadata_resourceAttributes", frame)
            self.assertTrue(frame.user_id.str.match(r"^(rater|synthetic)-\d+$").all())

    def test_project_identity_redaction_preserves_python_keywords(self):
        with TemporaryDirectory() as temp:
            mapping = Path(temp) / "mapping.json"
            mapping.write_text(
                json.dumps({
                    "sources": {},
                    "patterns": [[r"\bclass\b", "project-a"]],
                    "private_revisions": ["f" * 40],
                })
            )
            sanitizer = Anonymizer(mapping)
            source = "class Example:\n    label = 'class'\n"
            sanitized = sanitizer.python(source)
            compile(sanitized, "<test>", "exec")
            self.assertIn("class Example:", sanitized)
            self.assertIn("'project-a'", sanitized)
            text = sanitizer.record("class https://example.org/secret " + "f" * 40)
            self.assertEqual(text, "project-a [link-withheld] [revision-withheld]")

    def test_personal_names_are_withheld(self):
        samples = (
            "fix\n\nCo-authored-by: Jane Doe <xxxxxxxx>\n",
            '{\\"displayName\\": \\"Jane Doe\\", \\"userId\\": \\"123\\"}',
            '{"given": "Jane", "family": "Doe"}',
            "@Inproceedings{doe2025:XYZ,\\n  author = {Doe, Jane},\\n"
            "  title = {A Paper},\\n  booktitle = {Some Venue}\\n}",
            "@article{doe2025,\n-  author = {Doe, Jane and Roe, Rick},\n+}",
        )
        for text in samples:
            self.assertTrue(exposes_people(text), text)
            redacted = redact_people(text)
            self.assertFalse(exposes_people(redacted), redacted)
            self.assertNotIn("Doe", redacted)
        self.assertFalse(exposes_people("milestone = models.CharField()"))

    def test_privacy_audit_rejects_identifiable_paths_and_links(self):
        path = ROOT / "data/project-a_answers_merged.csv.gz"
        frame = pd.read_csv(path)
        for column, value in (
            ("C : metadata_repo_path", "external_repos/private-project"),
            ("C : output", "https://example.org/private-project"),
            ("C : input", "a" * 40),
        ):
            modified = frame.copy()
            modified.loc[0, column] = value
            payload = gzip.compress(modified.to_csv(index=False).encode(), mtime=0)
            with self.assertRaises(ValueError):
                audit_data_bytes(path.name, payload)

    def test_internal_repository_provenance_is_withheld(self):
        frame = pd.read_csv(ROOT / "provenance/repositories.csv")
        internal = frame[frame.analysis_repo.str.startswith("project-")]
        self.assertEqual(len(internal), 6)
        self.assertEqual(len(frame), 6)
        self.assertTrue(internal.url_from_gitmodules.isna().all())
        self.assertTrue(internal.preparation_gitlink.isna().all())
        manifest = verify_inputs()
        for entry in manifest["files"]:
            self.assertNotIn("source_name", entry)
            self.assertNotIn("source_sha256", entry)

    def test_reference_comparison_rejects_changed_results(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            shutil.copytree(ROOT / "reference", output, dirs_exist_ok=True)
            self.assertEqual(len(compare_tables(output)), 5)
            path = output / "figs/summary_by_model.csv"
            frame = pd.read_csv(path)
            frame.loc[0, "n"] += 1
            frame.to_csv(path, index=False)
            with self.assertRaises(AssertionError):
                compare_tables(output)

    def test_checksum_rejects_changed_input(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_text(
                json.dumps({
                    "files": [{"path": "changed.csv", "sha256": "0" * 64}],
                    "reference_tables": [],
                })
            )
            (root / "changed.csv").write_text("modified")
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                verify_inputs(root)

    def test_existing_results_are_not_overwritten(self):
        with TemporaryDirectory() as temp:
            existing = Path(temp) / "keep.txt"
            existing.write_text("keep")
            result = subprocess.run(
                [sys.executable, str(ROOT / "reproduce.py"), "--output", temp],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(existing.read_text(), "keep")

    def test_archive_excludes_private_and_unrelated_paths(self):
        for name in (
            ".env",
            "benchmark/credentials/key.json",
            "external_repos/project/a.py",
            "replication/.venv/a.py",
            "replication/results/x.csv",
            "src/__pycache__/a.pyc",
            ".git/config",
        ):
            self.assertFalse(included(name), name)
        for name in (
            "replication/data/example.csv.gz",
            "src/facade.py",
            "benchmark/export_results.py",
            "uv.lock",
            "LICENSE",
        ):
            self.assertTrue(included(name), name)


if __name__ == "__main__":
    unittest.main()
