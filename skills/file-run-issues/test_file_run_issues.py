#!/usr/bin/env python3
"""
Test suite for file-run-issues skill
"""

import json
import subprocess
import tempfile
from pathlib import Path


def run_skill(run_dir, **kwargs):
    """Run the skill and return parsed JSON output"""
    cmd = [
        "python3",
        str(Path(__file__).parent / "file-run-issues.py"),
        "--run-dir", str(run_dir),
        "--dry-run"
    ]

    for key, value in kwargs.items():
        if key == "min_severity":
            cmd.extend(["--min-severity", value])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Skill failed: {result.stderr}")

    return json.loads(result.stdout)


def test_empty_findings():
    """Test with no findings.jsonl"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "stack.json").write_text('{"model": "test"}')

        result = run_skill(run_dir)

        assert result["severity_counts"]["critical"] == 0
        assert result["penalty_score"] == 1.0
        assert result["top_findings"] == []
        assert result["model"] == "test"


def test_single_critical():
    """Test with one critical finding"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "stack.json").write_text('{"model": "test"}')
        (run_dir / "findings.jsonl").write_text(
            '{"id": "C1", "severity": "critical", "title": "Critical issue"}\n'
        )

        result = run_skill(run_dir)

        assert result["severity_counts"]["critical"] == 1
        assert result["penalty_score"] == 0.75
        assert len(result["top_findings"]) == 1


def test_severity_filtering():
    """Test min_severity filtering"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "stack.json").write_text('{"model": "test"}')
        (run_dir / "findings.jsonl").write_text(
            '{"id": "C1", "severity": "critical", "title": "Critical"}\n'
            '{"id": "H1", "severity": "high", "title": "High"}\n'
            '{"id": "M1", "severity": "medium", "title": "Medium"}\n'
            '{"id": "L1", "severity": "low", "title": "Low"}\n'
        )

        result_high = run_skill(run_dir, min_severity="high")

        assert result_high["severity_counts"]["critical"] == 1
        assert result_high["severity_counts"]["high"] == 1
        assert result_high["severity_counts"]["medium"] == 0
        assert result_high["severity_counts"]["low"] == 0


def test_top_findings_ordering():
    """Test that top findings are ordered by severity"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "stack.json").write_text('{"model": "test"}')
        (run_dir / "findings.jsonl").write_text(
            '{"id": "M1", "severity": "medium", "title": "Medium1"}\n'
            '{"id": "C1", "severity": "critical", "title": "Critical1"}\n'
            '{"id": "H1", "severity": "high", "title": "High1"}\n'
            '{"id": "M2", "severity": "medium", "title": "Medium2"}\n'
            '{"id": "L1", "severity": "low", "title": "Low1"}\n'
        )

        result = run_skill(run_dir)

        top_findings = result["top_findings"]
        severities = [f["severity"] for f in top_findings]
        assert severities == ["critical", "high", "medium", "medium", "low"]


def test_requirement_coverage():
    """Test requirement coverage calculation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "stack.json").write_text('{"model": "test"}')
        (run_dir / "findings.jsonl").write_text(
            '{"id": "R1", "kind": "requirement_missing", "severity": "high"}\n'
            '{"id": "R2", "kind": "requirement_partial", "severity": "medium"}\n'
            '{"id": "R3", "kind": "requirement_missing", "severity": "high"}\n'
        )

        result = run_skill(run_dir)

        # 3 total requirements, 3 have issues → 0 implemented
        assert result["requirement_coverage"] == 0.0


def test_penalty_score_calculation():
    """Test penalty score calculation"""
    test_cases = [
        ([], 1.0),  # No findings
        ([("critical",)], 0.75),  # 1 critical
        ([("high",)], 0.90),  # 1 high
        ([("medium",)], 0.97),  # 1 medium
        ([("low",)], 0.99),  # 1 low
        ([("critical",), ("high",)], 0.65),  # 1 critical + 1 high
    ]

    for findings_data, expected_score in test_cases:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "stack.json").write_text('{"model": "test"}')

            findings = [
                json.dumps({"id": f"F{i}", "severity": sev})
                for i, (sev,) in enumerate(findings_data)
            ]
            if findings:
                (run_dir / "findings.jsonl").write_text("\n".join(findings) + "\n")

            result = run_skill(run_dir)
            assert abs(result["penalty_score"] - expected_score) < 0.001, \
                f"Expected {expected_score}, got {result['penalty_score']} for {findings_data}"


def test_missing_stack_json():
    """Test graceful handling of missing stack.json"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        result = run_skill(run_dir)

        assert result["model"] == "unknown"


def test_iso_timestamp():
    """Test that evaluated_at is ISO 8601 UTC"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "stack.json").write_text('{"model": "test"}')

        result = run_skill(run_dir)

        # Should be ISO 8601 and end with Z
        assert result["evaluated_at"].endswith("Z")
        assert "T" in result["evaluated_at"]


if __name__ == "__main__":
    test_empty_findings()
    test_single_critical()
    test_severity_filtering()
    test_top_findings_ordering()
    test_requirement_coverage()
    test_penalty_score_calculation()
    test_missing_stack_json()
    test_iso_timestamp()

    print("All tests passed! ✓")
