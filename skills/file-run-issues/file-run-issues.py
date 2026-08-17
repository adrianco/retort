#!/usr/bin/env python3
"""
Aggregate a retort run's findings.jsonl into assessment.json.
Reads findings.jsonl and produces a machine-readable assessment.json summary
with severity counts, penalty score, requirement coverage, and top findings.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone


def load_findings(findings_path):
    """Load findings from findings.jsonl"""
    findings = []

    if not findings_path.exists():
        return findings

    try:
        with open(findings_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        finding = json.loads(line)
                        findings.append(finding)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Warning: Error reading findings.jsonl: {e}", file=sys.stderr)

    return findings


def severity_rank(severity):
    """Return numeric rank for severity (higher = more severe)"""
    ranking = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "info": 0
    }
    return ranking.get(severity, -1)


def filter_by_severity(findings, min_severity):
    """Filter findings by minimum severity"""
    min_rank = severity_rank(min_severity)
    return [f for f in findings if severity_rank(f.get("severity", "info")) >= min_rank]


def count_severities(findings):
    """Count findings by severity"""
    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0
    }

    for finding in findings:
        severity = finding.get("severity", "info")
        if severity in counts:
            counts[severity] += 1

    return counts


def compute_penalty_score(severity_counts):
    """Compute penalty score from severity counts"""
    score = 1.0
    score -= severity_counts["critical"] * 0.25
    score -= severity_counts["high"] * 0.10
    score -= severity_counts["medium"] * 0.03
    score -= severity_counts["low"] * 0.01

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, score))


def get_top_findings(findings, limit=5):
    """Get top findings sorted by severity"""
    # Sort by severity rank (descending), then preserve original order within same severity
    severity_groups = {}
    for i, finding in enumerate(findings):
        severity = finding.get("severity", "info")
        if severity not in severity_groups:
            severity_groups[severity] = []
        severity_groups[severity].append((i, finding))

    result = []
    for severity in ["critical", "high", "medium", "low", "info"]:
        if severity in severity_groups:
            # Preserve original order within severity
            result.extend([f for _, f in sorted(severity_groups[severity], key=lambda x: x[0])])

    return result[:limit]


def compute_requirement_coverage(findings, run_dir):
    """Compute requirement coverage"""
    # Count requirement findings
    requirement_findings = [
        f for f in findings
        if f.get("kind") in ["requirement_missing", "requirement_partial"]
    ]

    # Extract highest R-number from findings
    max_r = 0
    for finding in findings:
        finding_id = finding.get("id", "")
        if finding_id.startswith("R"):
            try:
                num = int(finding_id[1:])
                max_r = max(max_r, num)
            except:
                pass

    if max_r == 0:
        return None

    # Try to read evaluation.md for more info
    eval_md = run_dir / "evaluation.md"
    total_requirements = max_r

    if eval_md.exists():
        try:
            content = eval_md.read_text()
            # Count "implemented" status markers
            implemented = content.count("✓ implemented")
            if implemented > 0:
                total_requirements = max(total_requirements, implemented)
        except:
            pass

    if total_requirements == 0:
        return None

    # Count implemented requirements
    implemented_count = 0
    for finding in findings:
        if finding.get("kind") not in ["requirement_missing", "requirement_partial"]:
            # Non-requirement findings don't count
            continue
        if finding.get("kind") == "requirement_partial":
            implemented_count += 0.5  # Partial counts as half
        elif finding.get("kind") == "requirement_missing":
            pass  # Missing doesn't count

    # Also infer from findings that DON'T appear (if we have a sense of total)
    missing_count = len(requirement_findings)
    implemented_count = total_requirements - missing_count

    return max(0.0, min(1.0, implemented_count / total_requirements))


def read_model(run_dir):
    """Read model from stack.json"""
    stack_json = run_dir / "stack.json"

    if not stack_json.exists():
        return "unknown"

    try:
        with open(stack_json, 'r') as f:
            data = json.load(f)
            return data.get("model") or data.get("agent") or "unknown"
    except:
        return "unknown"


def format_summary(run_dir, severity_counts, penalty_score, top_findings, requirement_coverage, model):
    """Format summary for terminal output"""
    summary = []
    summary.append(f"Assessment written to {run_dir}/assessment.json")

    summary.append(f"  Severity counts: critical={severity_counts['critical']} high={severity_counts['high']} medium={severity_counts['medium']} low={severity_counts['low']} info={severity_counts['info']}")
    summary.append(f"  Penalty score:   {penalty_score:.4f}  (1.0 = clean, 0.0 = critical failures)")

    if requirement_coverage is not None:
        summary.append(f"  Req coverage:    {requirement_coverage * 100:.1f}%")

    summary.append(f"  Model:           {model}")

    if top_findings:
        top = top_findings[0]
        severity = top.get("severity", "info")
        title = top.get("title", "Unknown finding")
        summary.append(f"  Top finding:     [{severity}] {title}")

    return "\n".join(summary)


def main():
    parser = argparse.ArgumentParser(description="Aggregate run findings into assessment.json")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--min-severity", default="info",
                       choices=["critical", "high", "medium", "low", "info"],
                       help="Minimum severity to include (default: info)")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without writing file")

    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run_dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Load and filter findings
    findings_path = run_dir / "findings.jsonl"
    findings = load_findings(findings_path)
    filtered_findings = filter_by_severity(findings, args.min_severity)

    # Compute metrics
    severity_counts = count_severities(filtered_findings)
    penalty_score = compute_penalty_score(severity_counts)
    top_findings = get_top_findings(filtered_findings)
    requirement_coverage = compute_requirement_coverage(findings, run_dir)
    model = read_model(run_dir)

    # Create assessment object
    assessment = {
        "severity_counts": severity_counts,
        "penalty_score": round(penalty_score, 4),
        "top_findings": top_findings,
        "requirement_coverage": requirement_coverage,
        "model": model,
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    }

    # Handle dry-run
    if args.dry_run:
        print(json.dumps(assessment, indent=2))
        return

    # Write assessment.json atomically
    assessment_path = run_dir / "assessment.json"
    tmp_path = run_dir / "assessment.json.tmp"

    try:
        with open(tmp_path, 'w') as f:
            json.dump(assessment, f, indent=2)
        tmp_path.rename(assessment_path)
    except Exception as e:
        print(f"Warning: Atomic write failed, trying direct write: {e}", file=sys.stderr)
        try:
            with open(assessment_path, 'w') as f:
                json.dump(assessment, f, indent=2)
        except Exception as e:
            print(f"Error: Could not write assessment.json: {e}", file=sys.stderr)
            sys.exit(1)

    # Print summary
    summary = format_summary(run_dir, severity_counts, penalty_score, top_findings, requirement_coverage, model)
    print(summary)


if __name__ == "__main__":
    main()
