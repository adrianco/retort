#!/usr/bin/env python3
"""
File Run Issues aggregator - converts findings.jsonl into assessment.json
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Severity ordering (highest to lowest)
SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_WEIGHTS = {
    "critical": 0.25,
    "high": 0.10,
    "medium": 0.03,
    "low": 0.01,
    "info": 0.0
}


def severity_level(severity):
    """Return numeric level for severity (higher = more severe)"""
    try:
        return len(SEVERITY_ORDER) - SEVERITY_ORDER.index(severity)
    except ValueError:
        return 0


def should_include(finding_severity, min_severity):
    """Check if finding meets minimum severity threshold"""
    return severity_level(finding_severity) >= severity_level(min_severity)


def load_findings(findings_path):
    """Load findings from findings.jsonl"""
    findings = []
    if not findings_path.exists():
        return findings

    with open(findings_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Warning: could not parse line: {line}", file=sys.stderr)
    return findings


def filter_by_severity(findings, min_severity):
    """Filter findings by minimum severity"""
    return [f for f in findings if should_include(f.get("severity", "info"), min_severity)]


def count_severities(findings):
    """Count findings by severity level"""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        severity = finding.get("severity", "info")
        if severity in counts:
            counts[severity] += 1
    return counts


def compute_penalty_score(severity_counts):
    """Compute penalty score based on severity counts"""
    start = 1.0
    penalty = (
        severity_counts.get("critical", 0) * 0.25 +
        severity_counts.get("high", 0) * 0.10 +
        severity_counts.get("medium", 0) * 0.03 +
        severity_counts.get("low", 0) * 0.01
    )
    score = max(0.0, min(1.0, start - penalty))
    return round(score, 4)


def get_top_findings(findings, top_n=5):
    """Get top N findings sorted by severity (critical first, then preserve order)"""
    # Sort by severity level (descending), preserving original order within same severity
    sorted_findings = sorted(
        findings,
        key=lambda x: -severity_level(x.get("severity", "info"))
    )
    return sorted_findings[:top_n]


def compute_requirement_coverage(findings):
    """Compute requirement coverage from findings"""
    requirement_missing_count = 0
    requirement_partial_count = 0
    r_numbers = set()

    for finding in findings:
        kind = finding.get("kind", "")
        if kind in ["requirement_missing", "requirement_partial"]:
            if kind == "requirement_missing":
                requirement_missing_count += 1
            else:
                requirement_partial_count += 1

        # Extract R-numbers from finding IDs
        finding_id = finding.get("id", "")
        if finding_id.startswith("R") and finding_id[1:].isdigit():
            r_numbers.add(int(finding_id[1:]))

    if not r_numbers:
        return None

    total_requirements = max(r_numbers) if r_numbers else 0
    if total_requirements == 0:
        return None

    # Implemented = total - (missing + partial)
    implemented = total_requirements - (requirement_missing_count + requirement_partial_count)
    coverage = implemented / total_requirements if total_requirements > 0 else None

    return coverage


def read_model(stack_json_path):
    """Read model from stack.json"""
    if not stack_json_path.exists():
        return "unknown"

    try:
        with open(stack_json_path, 'r') as f:
            data = json.load(f)
            return data.get("model") or data.get("agent") or "unknown"
    except (json.JSONDecodeError, IOError):
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Aggregate findings.jsonl into assessment.json")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--min-severity", default="info", choices=SEVERITY_ORDER,
                        help="Minimum severity to include")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without writing file")

    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run_dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    findings_path = run_dir / "findings.jsonl"
    stack_json_path = run_dir / "stack.json"
    assessment_path = run_dir / "assessment.json"

    # Load and process findings
    all_findings = load_findings(findings_path)
    filtered_findings = filter_by_severity(all_findings, args.min_severity)

    severity_counts = count_severities(filtered_findings)
    penalty_score = compute_penalty_score(severity_counts)
    top_findings = get_top_findings(filtered_findings, top_n=5)
    requirement_coverage = compute_requirement_coverage(filtered_findings)
    model = read_model(stack_json_path)

    # Get current timestamp in ISO 8601 UTC format
    evaluated_at = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    # Build assessment object
    assessment = {
        "severity_counts": severity_counts,
        "penalty_score": penalty_score,
        "top_findings": top_findings,
        "requirement_coverage": requirement_coverage,
        "model": model,
        "evaluated_at": evaluated_at
    }

    if args.dry_run:
        print(json.dumps(assessment, indent=2))
    else:
        # Write atomically via tmp file
        tmp_path = assessment_path.with_suffix('.json.tmp')
        try:
            with open(tmp_path, 'w') as f:
                json.dump(assessment, f, indent=2)
            tmp_path.replace(assessment_path)
        except OSError as e:
            print(f"Warning: atomic rename failed, falling back to direct write: {e}",
                  file=sys.stderr)
            with open(assessment_path, 'w') as f:
                json.dump(assessment, f, indent=2)

        # Print summary
        print(f"Assessment written to {assessment_path}")
        counts_str = " ".join(f"{k}={v}" for k, v in severity_counts.items())
        print(f"  Severity counts: {counts_str}")
        print(f"  Penalty score:   {penalty_score:.4f}  (1.0 = clean, 0.0 = critical failures)")
        if requirement_coverage is not None:
            coverage_pct = requirement_coverage * 100
            print(f"  Req coverage:    {coverage_pct:.1f}%")
        else:
            print(f"  Req coverage:    unknown")
        print(f"  Model:           {model}")
        if top_findings:
            top = top_findings[0]
            severity = top.get("severity", "unknown")
            title = top.get("title", "")
            print(f"  Top finding:     [{severity}] {title}")


if __name__ == "__main__":
    main()
