"""C# scorer support: Cobertura parse, dotnet-test pass-rate, language wiring."""
from __future__ import annotations

from retort.scoring.scorers.code_quality import LINT_COMMANDS
from retort.scoring.scorers.defect_rate import _DEFECT_COMMANDS, _LOC_EXTENSIONS
from retort.scoring.scorers.maintainability import (
    _FUNCTION_PATTERNS,
    _SOURCE_EXTENSIONS,
)
from retort.scoring.scorers.test_coverage import (
    _TESTS_ONLY_COMMANDS,
    _parse_cobertura,
    _parse_test_pass_rate,
)

# _parse_cobertura only reads the root <coverage> attributes, so a root-only
# document is a faithful fixture.
_COBERTURA = '<coverage line-rate="0.85" lines-covered="17" lines-valid="20"/>'
_COBERTURA_EMPTY = '<coverage line-rate="0" lines-covered="0" lines-valid="0"/>'


def test_parse_cobertura_returns_line_rate(tmp_path):
    p = tmp_path / "coverage.cobertura.xml"
    p.write_text(_COBERTURA)
    assert _parse_cobertura(p) == 85.0


def test_parse_cobertura_empty_report_is_none(tmp_path):
    # An empty report (coverlet didn't instrument, e.g. single-project layout)
    # is no data — return None so the caller falls back to the pass rate rather
    # than scoring a false 0%.
    p = tmp_path / "coverage.cobertura.xml"
    p.write_text(_COBERTURA_EMPTY)
    assert _parse_cobertura(p) is None


def test_csharp_pass_rate_from_dotnet_summary():
    passed = "Passed! - Failed: 0, Passed: 3, Skipped: 0, Total: 3, Duration: 7 ms"
    assert _parse_test_pass_rate(passed, "csharp") == 1.0

    mixed = "Failed! - Failed: 1, Passed: 3, Skipped: 0, Total: 4, Duration: 9 ms"
    rate = _parse_test_pass_rate(mixed, "csharp")
    assert rate is not None and abs(rate - 0.75) < 1e-9


def test_csharp_wired_into_scorer_maps():
    assert "csharp" in LINT_COMMANDS
    assert "csharp" in _DEFECT_COMMANDS
    assert _LOC_EXTENSIONS["csharp"] == {".cs"}
    assert _SOURCE_EXTENSIONS["csharp"] == {".cs"}
    assert "csharp" in _FUNCTION_PATTERNS
    assert "csharp" in _TESTS_ONLY_COMMANDS


def test_csharp_method_regex_matches_real_methods():
    code = (
        "public int Add(int a, int b) => a + b;\n"
        '    private static string Name() => "x";\n'
        "    public async Task<int> FetchAsync(int id) { return id; }\n"
    )
    total = sum(len(p.findall(code)) for p in _FUNCTION_PATTERNS["csharp"])
    assert total == 3
