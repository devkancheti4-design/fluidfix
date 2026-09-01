# SPDX-License-Identifier: AGPL-3.0-or-later
"""Packaging hygiene, pinned. The publish workflow must gate PyPI on a green
suite; metadata, README teaching pointers, and .gitignore guard-state entries
must not silently regress. Workflow checks are structural string asserts so
this file needs no PyYAML (CI installs only `.[dev]`)."""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_publish_workflow_gates_on_tests():
    wf = (ROOT / ".github" / "workflows" / "publish.yml").read_text()
    jobs = wf.split("\njobs:\n", 1)[1]
    # a test job exists and runs the suite on 3.12
    test_job = jobs.split("\n  build:", 1)[0]
    assert re.search(r"^  test:$", test_job, re.M)
    assert 'python-version: "3.12"' in test_job
    assert "pip install -e . pytest pytest-cov" in test_job
    assert re.search(r"python -m pytest tests/ -q", test_job)
    # build and publish both refuse to run without it
    build_job = jobs.split("\n  build:", 1)[1].split("\n  publish:", 1)[0]
    assert re.search(r"^    needs: test$", build_job, re.M)
    publish_job = jobs.split("\n  publish:", 1)[1]
    assert re.search(r"^    needs: \[test, build\]$", publish_job, re.M)


def test_pyproject_metadata():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert meta["authors"][0]["name"] == "Devieswar Kancheti"
    assert meta["maintainers"][0]["name"] == "Devieswar Kancheti"
    assert meta["urls"]["Documentation"].endswith("docs/TEACHING.md")


def test_readme_teaching_pointers():
    readme = (ROOT / "README.md").read_text()
    assert "## Teach it your bugs" in readme
    assert "docs/TEACHING.md" in readme
    assert "examples/company_rules.py" in readme
    assert ".fluidfix/" in readme and ".gitignore" in readme


def test_gitignore_covers_guard_state():
    entries = (ROOT / ".gitignore").read_text().splitlines()
    for required in (".fluidfix/", ".coverage", "_fluidfix*.json"):
        assert required in entries
