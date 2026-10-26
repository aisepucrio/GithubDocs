"""Regression checks for lossless score exports; no external services are used."""

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from benchmark import export_results as exporter


class ExportResultsTests(unittest.TestCase):
    def test_all_raters_and_score_revisions_are_preserved(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        run = SimpleNamespace(
            id="run",
            dataset_name="dataset",
            name="experiment",
            dataset_run_items=[SimpleNamespace(trace_id="trace")],
        )
        scores = [
            SimpleNamespace(
                id=f"s{i}",
                trace_id="trace",
                name="clarity",
                value=value,
                data_type="NUMERIC",
                author_user_id=user,
                comment=f"comment-{i}",
                source="ANNOTATION",
                created_at=now,
                updated_at=now,
            )
            for i, (user, value) in enumerate((
                ("rater-a", 2),
                ("rater-b", 4),
                ("rater-a", 3),
            ))
        ]
        generation = SimpleNamespace(
            id="generation",
            type="GENERATION",
            model="test-model",
            usage=SimpleNamespace(input=10, output=4, total=14, unit="TOKENS"),
            usage_details={"input": 10, "output": 4},
            cost_details={"total": 0.1},
        )
        span = SimpleNamespace(
            id="parent",
            type="SPAN",
            usage=SimpleNamespace(input=10, output=4, total=14, unit="TOKENS"),
        )
        trace = SimpleNamespace(
            id="trace",
            input={},
            metadata={"success": True},
            output="document",
            html_path="/trace",
            timestamp=now,
            observations=[generation, span],
            total_cost=0.1,
            latency=2.5,
        )
        client = Mock()
        client.get_dataset_run.return_value = run
        client.api.trace.get.return_value = trace
        with (
            TemporaryDirectory() as temp,
            patch.object(exporter, "require_langfuse_client", return_value=client),
            patch.object(exporter, "_fetch_all_scores", return_value=scores),
        ):
            result = exporter.export_dataset_run_results(
                dataset_name="dataset",
                run_name="experiment",
                output_path=str(Path(temp) / "results.csv"),
                wait_for_scores_enabled=False,
            )
            wide = pd.read_csv(result["output_path"])
            long = pd.read_csv(result["scores_path"])
            observations = [
                json.loads(line)
                for line in Path(result["observations_path"]).read_text().splitlines()
            ]
        self.assertEqual(len(long), 3)
        self.assertEqual(long["value"].tolist(), [2, 4, 3])
        self.assertEqual(
            long["author_user_id"].tolist(), ["rater-a", "rater-b", "rater-a"]
        )
        self.assertEqual(
            long["comment"].tolist(), ["comment-0", "comment-1", "comment-2"]
        )
        self.assertEqual(wide.iloc[0]["clarity"], 3)
        self.assertEqual(
            wide.iloc[0]["total_tokens"], 14
        )  # parent span not double counted
        self.assertEqual(wide.iloc[0]["total_cost"], 0.1)
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0]["usage_details"], {"input": 10, "output": 4})

    def test_missing_or_non_token_usage_is_not_zero(self):
        self.assertIsNone(exporter._token_totals([])["total_tokens"])
        observation = {
            "type": "GENERATION",
            "usage_unit": "CHARACTERS",
            "input": 10,
            "output": 4,
            "total": 14,
        }
        self.assertIsNone(exporter._token_totals([observation])["total_tokens"])


if __name__ == "__main__":
    unittest.main()
