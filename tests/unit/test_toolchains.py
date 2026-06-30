"""Tests for the language-toolchain preflight."""

from __future__ import annotations

import subprocess

from retort.playpen.toolchains import (
    Toolchain,
    ensure_toolchains,
    format_report,
    required_toolchains,
)


class TestRequiredToolchains:
    def test_maps_known_languages(self):
        tcs = required_toolchains(["go", "rust", "csharp"])
        probes = {t.probe for t in tcs}
        assert probes == {"go", "cargo", "dotnet"}

    def test_is_case_insensitive_and_dedups_shared_probe(self):
        # typescript + javascript both probe `node` -> one entry; TS uppercased.
        tcs = required_toolchains(["TypeScript", "javascript"])
        assert [t.probe for t in tcs] == ["node"]

    def test_ignores_unknown_languages(self):
        assert required_toolchains(["go", "cobol", "whitespace"]) == [
            t for t in required_toolchains(["go"])
        ]

    def test_aliases_resolve(self):
        assert required_toolchains(["ts"])[0].probe == "node"
        assert required_toolchains(["c#"])[0].probe == "dotnet"


class TestEnsureToolchains:
    def test_present_toolchain_not_installed(self):
        calls = []

        def runner(*a, **k):  # should never be called
            calls.append(a)
            return subprocess.CompletedProcess(a, 0, "", "")

        statuses = ensure_toolchains(
            ["go"], install=True, runner=runner, which=lambda p: "/usr/bin/" + p
        )
        assert len(statuses) == 1
        assert statuses[0].present and not statuses[0].installed
        assert calls == []  # nothing installed because it was already present

    def test_missing_toolchain_is_installed(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr("shutil.which", lambda p: "/opt/homebrew/bin/brew" if p == "brew" else None)

        seen = {"go": False}
        installed_cmds = []

        def runner(argv, **k):
            installed_cmds.append(argv)
            seen["go"] = True  # after install, go appears on PATH
            return subprocess.CompletedProcess(argv, 0, "ok", "")

        def which(p):
            if p == "go":
                return "/opt/homebrew/bin/go" if seen["go"] else None
            return None

        statuses = ensure_toolchains(["go"], install=True, runner=runner, which=which)
        assert statuses[0].present and statuses[0].installed
        assert installed_cmds == [["brew", "install", "go"]]

    def test_install_failure_records_error_and_does_not_raise(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr("shutil.which", lambda p: "/opt/homebrew/bin/brew" if p == "brew" else None)

        def runner(argv, **k):
            return subprocess.CompletedProcess(argv, 1, "", "brew: formula broke")

        statuses = ensure_toolchains(
            ["rust"], install=True, runner=runner, which=lambda p: None
        )
        assert statuses[0].present is False
        assert statuses[0].installed is False
        assert "broke" in statuses[0].error

    def test_install_false_only_reports(self):
        ran = []
        statuses = ensure_toolchains(
            ["go"],
            install=False,
            runner=lambda *a, **k: ran.append(a),
            which=lambda p: None,
        )
        assert statuses[0].present is False
        assert ran == []

    def test_no_package_manager_records_error(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "sunos5")
        statuses = ensure_toolchains(
            ["go"], install=True, runner=lambda *a, **k: None, which=lambda p: None
        )
        assert statuses[0].present is False
        assert "package manager" in statuses[0].error

    def test_runner_oserror_is_caught(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr("shutil.which", lambda p: "/opt/homebrew/bin/brew" if p == "brew" else None)

        def runner(argv, **k):
            raise OSError("brew vanished")

        statuses = ensure_toolchains(
            ["go"], install=True, runner=runner, which=lambda p: None
        )
        assert statuses[0].present is False
        assert "brew vanished" in statuses[0].error


class TestFormatReport:
    def test_lines_reflect_state(self):
        statuses = ensure_toolchains(["go"], install=False, which=lambda p: "/bin/go")
        present_line = format_report(statuses, installed_action=False)[0]
        assert "present" in present_line and "Go" in present_line

        missing = ensure_toolchains(["go"], install=False, which=lambda p: None)
        missing_line = format_report(missing, installed_action=False)[0]
        assert "missing" in missing_line
