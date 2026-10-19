"""Cheap checks that keep the repository easy to find your way around and safe to share."""

import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "databricks.yml",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".github/workflows/checks.yml",
    ".github/workflows/deploy-databricks-preview.yml",
    ".github/workflows/deploy-databricks.yml",
    "resources/buildabida_full_pipeline.job.yml",
    "notebooks/06_data_quality/README.md",
    "docs/operations.md",
]
# only these Markdown files belong in the root. History goes in docs/change-history
ROOT_MARKDOWN = {"README.md", "CONTRIBUTING.md"}
SECRET_PATTERNS = [
    re.compile(r"dapi[0-9a-f]{32}"),  # Databricks personal access token
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"),  # GitHub token
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def tracked_files():
    try:
        output = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
        return [ROOT / line for line in output.splitlines() if (ROOT / line).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [path for path in ROOT.rglob("*") if ".git" not in path.parts]


def test_required_files_exist():
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    assert not missing


def test_root_has_no_loose_markdown():
    assert {path.name for path in ROOT.glob("*.md")} == ROOT_MARKDOWN


def test_every_ipynb_notebook_is_valid_json_with_cells():
    for path in ROOT.glob("notebooks/**/*.ipynb"):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["cells"], path
        assert "nbformat" in notebook, path


def test_every_source_notebook_has_the_databricks_header_and_parses():
    for path in [*ROOT.glob("notebooks/**/*.py"), *ROOT.glob("notebooks/**/*.sql")]:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert first in {
            "# Databricks notebook source",
            "-- Databricks notebook source",
        }, path
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_no_tokens_or_private_keys_are_committed():
    found = []
    for path in tracked_files():
        if path.suffix in {".png", ".webp", ".jpg", ".zip"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        found += [
            f"{path.relative_to(ROOT)}"
            for pattern in SECRET_PATTERNS
            if pattern.search(text)
        ]
    assert not found


def test_codeowners_paths_exist_and_every_line_has_two_owners():
    for line in (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        assert len(owners) >= 2, line
        assert all(re.fullmatch(r"@[A-Za-z0-9-]+", owner) for owner in owners), line
        if pattern != "*":
            matches = list(ROOT.glob(pattern.strip("/")))
            assert matches, pattern
