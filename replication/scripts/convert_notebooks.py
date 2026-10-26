"""Extract the authors' analysis cells, replacing only notebook I/O.

The generated scripts retain cell numbers to make the adaptation auditable.
No notebook outputs, widget metadata or installation/download cells are copied.
"""

import argparse
import json
from pathlib import Path

try:
    from .anonymize import Anonymizer
except ImportError:
    from anonymize import Anonymizer

ROOT = Path(__file__).resolve().parents[1]


def convert(source, target, anonymizer, rq3=False):
    notebook = json.loads(source.read_text())
    last = 26 if rq3 else 36
    chunks = [
        '"""Adapted from the supplied analysis notebook; see docs/methodology.md."""\n',
        "from pathlib import Path\nimport os\nimport matplotlib\n"
        "matplotlib.use('Agg')\n"
        "display = print\n",
    ]
    for number, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code" or number in (2, last):
            continue
        code = "".join(cell["source"])
        if number == 4:
            code = "DATA_DIR = os.environ['DOME_DATA_DIR']\n"
            if rq3:
                code += (
                    "GD_PATHS = sorted(glob.glob(os.path.join(DATA_DIR, "
                    "'*_answers_merged.csv.gz')))\n"
                    "CC_PATH = os.path.join(DATA_DIR, 'claude_code_answers.csv.gz')\n"
                )
            else:
                code += (
                    "paths = sorted(glob.glob(os.path.join(DATA_DIR, "
                    "'*_answers_merged.csv.gz')))\n"
                )
        code = code.replace(
            ".replace('_answers_merged.csv', '')",
            ".replace('_answers_merged.csv.gz', '')",
        )
        code = code.replace("plt.show(); plt.close(fig)", "plt.close(fig)")
        # Coded annotations are optional inputs, separate from generated files.
        for filename in (
            "low_score_comments_CODED.csv",
            "rq3_low_score_comments_CODED.csv",
        ):
            code = code.replace(
                f"CODED = '{filename}'", f"CODED = os.path.join(DATA_DIR, '{filename}')"
            )
        code = anonymizer.python(code)
        code = code.replace(
            "_out.str.len().where(~FAILED)",
            "pd.to_numeric(raw['C : output_char_count']).where(~FAILED)",
        )
        code = code.replace(
            "out.str.len().where(out.ne(''))",
            "pd.to_numeric(raw['C : output_char_count']).where(out.ne(''))",
        )
        chunks.append(f"\n# Original notebook cell {number}\n{code}\n")
    figure_dir = "figs_rq3" if rq3 else "figs"
    chunks.append(
        "\n# Additional machine-readable exports; no change to the analysis.\n"
        f"ann.to_csv('{figure_dir}/annotations.csv', index=False)\n"
        f"ctx.to_csv('{figure_dir}/contexts.csv', index=False)\n"
    )
    if not rq3:
        chunks.append(
            "agree.to_csv('figs/inter_annotator_agreement.csv', index=False)\n"
            "tests = []\nfor rq, d in rq_frames():\n"
            "    p, dunn = kruskal_by_model(d, 'Overall')\n"
            "    tests.append({'rq': rq, 'kruskal_p': p})\n"
            "    if dunn is not None:\n"
            "        dunn.to_csv(f'figs/dunn_holm_{rq.lower()}.csv')\n"
            "pd.DataFrame(tests).to_csv('figs/kruskal_tests.csv', index=False)\n"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(chunks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rq12-notebook", type=Path, required=True)
    parser.add_argument("--rq3-notebook", type=Path, required=True)
    parser.add_argument("--anonymization-map", type=Path, required=True)
    args = parser.parse_args()
    anonymizer = Anonymizer(args.anonymization_map)
    convert(args.rq12_notebook, ROOT / "analysis/rq1_rq2.py", anonymizer)
    convert(args.rq3_notebook, ROOT / "analysis/rq3.py", anonymizer, rq3=True)


if __name__ == "__main__":
    main()
