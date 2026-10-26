"""Build a curated archive from committed blobs, excluding local/private files."""

import argparse
import hashlib
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

try:
    from .anonymize import audit_data_bytes
except ImportError:
    from anonymize import audit_data_bytes

REPO = Path(__file__).resolve().parents[2]


def included(name):
    path = PurePosixPath(name)
    if any(
        part in {".git", ".venv", "__pycache__", "credentials", "results", ".aws"}
        for part in path.parts
    ):
        return False
    if name in {
        "LICENSE",
        "README.md",
        "pyproject.toml",
        "uv.lock",
        "main.py",
        "util.py",
        "conf/config_example.toml",
        "tests/test_export_results.py",
    }:
        return True
    if name.startswith("replication/"):
        return path.suffix not in {".pyc", ".zip"} and not path.name.startswith(".env")
    if name.startswith("src/"):
        return path.suffix == ".py"
    if name.startswith("benchmark/"):
        return len(path.parts) == 2 and (
            path.suffix == ".py" or path.name == "README.md"
        )
    return name.startswith("prompt/") and path.suffix == ".jinja"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = (
        git("rev-parse", "--verify", f"{args.revision}^{{commit}}").decode().strip()
    )
    paths = sorted(
        name
        for name in git("ls-tree", "-r", "--name-only", revision).decode().splitlines()
        if included(name)
    )
    if "replication/manifest.json" not in paths:
        parser.error("Selected commit does not contain the replication package")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite a previous release or its checksum accidentally.
    if (
        args.output.exists()
        or args.output.with_suffix(args.output.suffix + ".sha256").exists()
    ):
        parser.error("Archive/checksum already exists; choose a new output filename")
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in paths:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            content = git("show", f"{revision}:{name}")
            if name.startswith("replication/data/") and name.endswith(".csv.gz"):
                audit_data_bytes(name, content)
            archive.writestr(info, content)
        info = zipfile.ZipInfo("ARCHIVE_INFO.txt", date_time=(1980, 1, 1, 0, 0, 0))
        archive.writestr(
            info,
            "Review archive. Source commit and Git history are withheld.\n"
            "Content checksums: replication/manifest.json\n"
            "Subject submodules are not bundled. "
            "See replication/docs/reexecution.md.\n",
        )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        f"{digest}  {args.output.name}\n"
    )
    print(f"Archived {len(paths)} committed files from {revision} to {args.output}")


if __name__ == "__main__":
    main()
