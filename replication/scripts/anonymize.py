"""Project anonymization using a private, untracked mapping supplied by maintainers."""

import csv
import gzip
import io
import json
import re
import tokenize
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
URL = re.compile(r"(?:https?://|git@)[^\s<>\"'`\\)\]]+", re.IGNORECASE)
REVISION = re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)
PROJECTS = {
    "project-a": "external_repos/project-a",
    "project-b": "external_repos/project-b",
    "project-c": "external_repos/project-c",
    "project-d": "external_repos/project-d",
    "project-e": "external_repos/project-e",
    "project-f": "external_repos/project-f",
}
# Commit trailers, notebook account metadata and citation entries name people.
TRAILER = re.compile(
    r"\b(co-authored-by|signed-off-by|reviewed-by|reported-by|helped-by):"
    r"[ \t]*[^<\r\n\\\"]+",
    re.IGNORECASE,
)
ACCOUNT = re.compile(
    r"((?:\\)*\"(?:displayName|userId|emailAddress|photoUrl)(?:\\)*\"\s*:\s*"
    r"(?:\\)*\")[^\"\\]*"
)
CSL_NAME = re.compile(
    r"((?:\\)*\"given(?:\\)*\"\s*:\s*(?:\\)*\")[^\"\\]*"
    r"((?:\\)*\"\s*,\s*(?:\\)*\"family(?:\\)*\"\s*:\s*(?:\\)*\")[^\"\\]*"
)
# Entries end with a closing brace on its own (possibly diff-prefixed) line; the
# newline may be literal or escaped inside serialized prompts.
CITATION = re.compile(
    r"@(?:inproceedings|article|misc|inbook|incollection|book|phdthesis|"
    r"mastersthesis|techreport|software|online)\{.{0,3000}?(?:\n|\\n)[+\- ]?\}",
    re.IGNORECASE | re.DOTALL,
)
CITATION_KEY = re.compile(r"^(@\w+\{)[^,\s]+,")
CITATION_FIELD = re.compile(
    r"\b(author|editor|title|booktitle|journal|doi|url|note)(\s*=\s*)"
    r"(?:\{[^{}]*\}|\"[^\"]*\")",
    re.IGNORECASE,
)
WITHHELD_PERSON = "[name-withheld]"


def _citation(match):
    entry = CITATION_KEY.sub(r"\1anonymous,", match[0])
    return CITATION_FIELD.sub(r"\1\2{[withheld]}", entry)


def redact_people(text):
    """Withhold personal names carried by trailers, notebook metadata and BibTeX."""
    text = TRAILER.sub(lambda m: f"{m[1]}: {WITHHELD_PERSON} ", text)
    text = ACCOUNT.sub(r"\1[withheld]", text)
    text = CSL_NAME.sub(r"\1[withheld]\2[withheld]", text)
    return CITATION.sub(_citation, text)


def exposes_people(text):
    if any(
        m[0].split(":", 1)[1].strip() != WITHHELD_PERSON for m in TRAILER.finditer(text)
    ):
        return True
    if any(not m[0].endswith("[withheld]") for m in ACCOUNT.finditer(text)):
        return True
    if any(m[0].count("[withheld]") != 2 for m in CSL_NAME.finditer(text)):
        return True
    return any(
        "{[withheld]}" not in field[0]
        for entry in CITATION.finditer(text)
        for field in CITATION_FIELD.finditer(entry[0])
    )


class Anonymizer:
    def __init__(self, mapping_path):
        mapping_path = Path(mapping_path).resolve()
        if mapping_path.is_relative_to(REPOSITORY):
            raise ValueError(
                "Keep the private anonymization mapping outside the repository"
            )
        config = json.loads(mapping_path.read_text(encoding="utf-8"))
        self.sources = config["sources"]
        self.patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in config["patterns"]
        ]
        self.private_revisions = config.get("private_revisions", [])

    def names(self, text):
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        for revision in self.private_revisions:
            text = text.replace(revision, "[revision-withheld]")
        return text

    def record(self, text):
        """Redact indirect links as well as explicit project names in data text."""
        text = URL.sub("[link-withheld]", text)
        text = REVISION.sub("[revision-withheld]", text)
        return redact_people(self.names(text))

    def python(self, source):
        """Change project names inside strings/comments, preserving Python keywords."""
        tokens = []
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in (tokenize.STRING, tokenize.COMMENT):
                token = token._replace(string=self.names(token.string))
            tokens.append(token)
        return tokenize.untokenize(tokens)


def validate_dataset(frame, source_name):
    """Reject identifiable repository paths and publication links before analysis."""
    if not frame["C : metadata_repo_path"].isin(PROJECTS.values()).all():
        raise ValueError(f"Unexpected repository identifier in {source_name}")
    for column in ("C : input", "C : prompt", "C : output"):
        if column not in frame:
            continue
        for text in frame[column].dropna().astype(str):
            if URL.search(text) or REVISION.search(text):
                raise ValueError(
                    f"Unredacted link or revision in {source_name}: {column}"
                )
            if exposes_people(text):
                raise ValueError(f"Unredacted personal name in {source_name}: {column}")


def audit_data_bytes(name, payload):
    """Check a compressed export without requiring the analysis dependencies."""
    csv.field_size_limit(2**31 - 1)
    allowed = {f"{project}_answers_merged.csv.gz" for project in PROJECTS}
    allowed.add("claude_code_answers.csv.gz")
    if Path(name).name not in allowed:
        raise ValueError("Unexpected dataset filename")
    text = gzip.decompress(payload).decode("utf-8")
    for row in csv.DictReader(io.StringIO(text)):
        if row["C : metadata_repo_path"] not in PROJECTS.values():
            raise ValueError("Unexpected repository identifier in dataset")
        if int(row["C : output_char_count"]) < 0:
            raise ValueError("Invalid original output length")
        for value in row.values():
            if URL.search(value) or REVISION.search(value):
                raise ValueError("Unredacted URL or revision in dataset")
            if exposes_people(value):
                raise ValueError("Unredacted personal name in dataset")
