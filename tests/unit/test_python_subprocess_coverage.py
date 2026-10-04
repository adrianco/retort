"""Python coverage counts a server the TESTS launch as a subprocess (ATDD protocol driver).

exp-83: a Python acceptance suite that starts the server with `sys.executable -m pkg`
and talks to it over stdio measured 67% — the server code ran in another process.
"""
import configparser
import re
import subprocess
import sys
import textwrap

import pytest

from retort.scoring.scorers.test_coverage import _python_subprocess_coverage_rc


def _project(tmp_path, *, subprocess_driver: bool):
    pkg = tmp_path / "demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(textwrap.dedent("""\
        def double(n):
            return n * 2

        def triple(n):
            return n * 3

        if __name__ == "__main__":
            print(double(21))
            print(triple(3))
        """))
    (tmp_path / "tests").mkdir()
    body = (
        "import subprocess, sys\n"
        "def test_cli():\n"
        "    out = subprocess.run([sys.executable, '-m', 'demo'], capture_output=True, text=True).stdout\n"
        "    assert out.split() == ['42', '9']\n"
        if subprocess_driver else
        "def test_nothing():\n    assert True\n")
    (tmp_path / "tests" / "test_demo.py").write_text(body)
    return tmp_path


def test_only_used_when_tests_start_a_subprocess(tmp_path):
    assert _python_subprocess_coverage_rc(_project(tmp_path, subprocess_driver=False)) is None


def test_rc_enables_subprocess_patch_and_keeps_project_settings(tmp_path):
    proj = _project(tmp_path, subprocess_driver=True)
    (proj / ".coveragerc").write_text("[run]\nomit = */migrations/*\n[report]\nskip_empty = true\n")
    rc = _python_subprocess_coverage_rc(proj)
    cfg = configparser.ConfigParser()
    cfg.read(rc)
    assert cfg.get("run", "patch") == "subprocess"
    assert cfg.get("run", "omit") == "*/migrations/*"
    assert cfg.get("report", "skip_empty") == "true"
    assert rc.parent != proj  # never written into the workspace


def test_subprocess_server_code_is_counted(tmp_path):
    pytest.importorskip("pytest_cov")
    import coverage
    if tuple(int(x) for x in coverage.__version__.split(".")[:2]) < (7, 10):
        pytest.skip("coverage < 7.10 has no `patch = subprocess`")
    proj = _project(tmp_path, subprocess_driver=True)
    base = [sys.executable, "-m", "pytest", "--cov=.", "-p", "no:cacheprovider",
            "--cov-report=term", "-q", "--tb=short"]

    def total(cmd):
        out = subprocess.run(cmd, cwd=proj, capture_output=True, text=True).stdout
        return int(re.search(r"^TOTAL.*?(\d+)%", out, re.M).group(1))

    without = total(base)
    rc = _python_subprocess_coverage_rc(proj)
    with_rc = total([*base[:4], "--cov-config", str(rc), *base[4:]])
    assert with_rc > without
    assert with_rc == 100
