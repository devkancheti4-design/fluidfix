# SPDX-License-Identifier: AGPL-3.0-or-later
"""What should this team test FIRST — the question that decides how much of a
repo fluidfix can maintain."""
import subprocess

from fluidfix.hotspots import (bugfix_churn, coverage_to_reach, rank_hotspots,
                               _statement_density)


def _repo(tmp_path, commits):
    def sh(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], capture_output=True)
    sh("init", "-q")
    sh("config", "user.email", "t@t"); sh("config", "user.name", "t")
    for msg, files in commits:
        for f, body in files.items():
            p = tmp_path / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        sh("add", "-A"); sh("commit", "-q", "-m", msg)
    return str(tmp_path)


def test_only_bugfix_commits_count(tmp_path):
    root = _repo(tmp_path, [
        ("add feature",        {"src/a.c": "int a = 1;\n"}),
        ("fix crash in b",     {"src/b.c": "int b = 2;\n"}),
        ("refactor naming",    {"src/a.c": "int a = 3;\n"}),
        ("fix wrong sign",     {"src/b.c": "int b = 4;\n"}),
    ])
    churn, scanned, fixes = bugfix_churn(root)
    assert scanned == 4 and fixes == 2
    assert churn["src/b.c"] == 2
    assert "src/a.c" not in churn          # feature + refactor, not fixes


def test_tests_and_samples_are_never_recommended(tmp_path):
    root = _repo(tmp_path, [
        ("fix everything", {
            "src/real.c": "int x = 1;\n",
            "test/test_real.c": "int t;\n",
            "samples/demo.c": "int d;\n",
            "shared/helper.c": "int h;\n",
            "extern/dep.c": "int e;\n"}),
    ])
    churn, _, _ = bugfix_churn(root)
    assert set(churn) == {"src/real.c"}


def test_coverage_to_reach_reports_files_not_lines(tmp_path):
    import collections
    churn = collections.Counter({"a": 50, "b": 30, "c": 15, "d": 5})
    got = dict(coverage_to_reach(churn, shares=(0.5, 0.8, 1.0)))
    assert got[0.5] == 1        # "a" alone is 50%
    assert got[0.8] == 2        # a+b = 80%
    assert got[1.0] == 4


def test_ranking_prefers_the_uncovered(tmp_path):
    import collections
    body = "int f(void) { int x = 1; if (x) { return x; } return 0; }\n" * 20
    for f in ("src/hot.c", "src/cold.c"):
        p = tmp_path / f; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    churn = collections.Counter({"src/hot.c": 5, "src/cold.c": 5})
    covered = {"src/cold.c": set(range(1, 200))}      # cold is well covered
    rows = rank_hotspots(str(tmp_path), churn, covered)
    assert rows[0]["file"] == "src/hot.c"


def test_declaration_headers_are_not_top_recommendations(tmp_path):
    """A header of prototypes cannot be tested directly, and its coverage
    cannot be measured honestly — inline bodies are attributed to the caller.
    Measured on Box2D: box2d.h ranked #1 until this was handled."""
    decls = "\n".join(f"int api_{i}( const void* p );" for i in range(80))
    impl = "\n".join(f"int f{i}(void) {{ int x = {i}; return x; }}"
                     for i in range(80))
    (tmp_path / "api.h").write_text(decls)
    (tmp_path / "impl.c").write_text(impl)
    import collections
    churn = collections.Counter({"api.h": 10, "impl.c": 6})
    rows = rank_hotspots(str(tmp_path), churn, covered={})
    assert rows[0]["file"] == "impl.c"          # despite fewer defects
    assert any(r["file"] == "api.h" and r["declarations"] for r in rows)


def test_statement_density_ignores_prose():
    """Doc comments contain 'if', 'for' and '=' in English. Counting them
    read Box2D's box2d.h as implementation at 0.198."""
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "doc.h").write_text(
        "/** You can query the world if you want, for example x = 1.\n"
        " * More prose that mentions if and for and equals =.\n"
        " */\nint api_call( const void* p );\n")
    assert _statement_density(str(d / "doc.h")) == 0.0


def test_not_a_git_repo_answers_instead_of_raising(tmp_path):
    churn, scanned, fixes = bugfix_churn(str(tmp_path))
    assert churn == {} and scanned == 0 and fixes == 0


def test_version_is_single_source_and_current():
    """`__version__` sat at 0.9.1 through the 0.10.0 AND 0.11.0 releases —
    two versions shipped advertising the wrong number to anyone reading it.
    pyproject now derives the distribution version from this attribute, so a
    drift would mis-tag a release. This pins them together."""
    import pathlib, re
    import fluidfix
    root = pathlib.Path(fluidfix.__file__).resolve().parents[2]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    # the distribution must derive its version from the package attribute
    assert 'dynamic = ["version"]' in pyproject
    assert 'attr = "fluidfix.__version__"' in pyproject
    # and the attribute must look like a release, not a placeholder
    assert re.fullmatch(r"\d+\.\d+\.\d+", fluidfix.__version__), fluidfix.__version__
    # the changelog's newest entry must be the version we are shipping
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    newest = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M).group(1)
    assert newest == fluidfix.__version__, (
        f"CHANGELOG says {newest}, __version__ says {fluidfix.__version__}")
