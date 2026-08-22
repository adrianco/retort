"""The provisioned `venv/` must never be scored as agent-authored source.

retort provisions a venv INTO each python workspace
(local_runner.PYTHON_VENV_DIR = "venv"). SKIP_PARTS listed only the dotted
`.venv`, so run-time scoring walked venv/lib/python3.x/site-packages and scored
the standard library as if the agent had written it.

Measured on exp-61 before the fix: maintainability recorded 0.27 where a rescore
of the same artifacts gives 1.00, and token_efficiency recorded a perfect 1.00
where the truth is 0.02 -- wrong in both directions, the 1.00 being the more
dangerous because it reads as a flawless result.
"""
from __future__ import annotations

from pathlib import Path

from retort.playpen.local_runner import PYTHON_VENV_DIR
from retort.scoring.scorers._common import SKIP_PARTS, is_skipped, iter_source_files


def test_provisioned_venv_dir_name_is_skipped():
    # Pins the two together: renaming PYTHON_VENV_DIR without updating
    # SKIP_PARTS silently reintroduces the bug.
    assert PYTHON_VENV_DIR in SKIP_PARTS


def test_is_skipped_covers_a_site_packages_path():
    assert is_skipped(Path("w/venv/lib/python3.11/site-packages/click/core.py"))
    assert not is_skipped(Path("w/app.py"))


def test_iter_source_files_ignores_the_workspace_venv(tmp_path: Path):
    (tmp_path / "app.py").write_text("def handler():\n    return 1\n")
    (tmp_path / "test_app.py").write_text("def test_handler():\n    assert True\n")
    vendored = tmp_path / PYTHON_VENV_DIR / "lib" / "python3.11" / "site-packages" / "click"
    vendored.mkdir(parents=True)
    # A single large vendored module is enough: it is the LOC, not the file
    # count, that wrecks the per-file metrics.
    (vendored / "core.py").write_text("def vendored():\n" + "    pass\n" * 500)

    found = {p.name for p in iter_source_files(tmp_path, ".py")}
    assert found == {"app.py", "test_app.py"}, f"venv leaked into scoring: {found}"
