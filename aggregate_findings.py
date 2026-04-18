#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

def parse_args():
    run_dir = None
    min_severity = "info"
    dry_run = False

    for i, arg in enumerate(sys.argv[1:]):
        if arg.startswith("run_dir="):
            run_dir = arg.split("=", 1)[1]
        elif arg.startswith("min_severity="):
            min_severity = arg.split("=", 1)[1]
        elif arg == "--dry-run" or arg.startswith("dry_run="):
            dry_run = True if arg == "--dry-run" else arg.split("=")[1].lower() == "true"
        elif arg.startswith("tracker="):
            pass  # Ignored, not used by this skill

    if not run_dir:
        print("Error: run_dir parameter required", file=sys.stderr)
        sys.exit(1)

    return run_dir, min_severity, dry_run

def severity_value(sev: str) -> int:
    return SEVERITY_ORDER.get(sev, -1)

def load_findings(findings_path: Path) -> list[dict[str, Any]]:
    findings = []
    if not findings_path.exists():
        return findings

    with open(findings_path) as f:
        for line in f:
            line = line.strip()
            if line:
                findings.append(json.loads(line))
    return findings

def filter_by_severity(findings: list[dict], min_severity: str) -> list[dict]:
    min_val = severity_value(min_severity)
    return [f for f in findings if severity_value(f.get("severity", "info")) >= min_val]

def count_severities(findings: list[dict]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        sev = finding.get("severity", "info")
        if sev in counts:
            counts[sev] += 1
    return counts

def compute_penalty_score(severity_counts: dict[str, int]) -> float:
    score = 1.0
    score -= severity_counts["critical"] * 0.25
    score -= severity_counts["high"] * 0.10
    score -= severity_counts["medium"] * 0.03
    score -= severity_counts["low"] * 0.01
    return max(0.0, min(1.0, score))

def collect_top_findings(findings: list[dict], top_n: int = 5) -> list[dict]:
    # Sort by severity (descending), then preserve original order within same severity
    def severity_key(f):
        return -severity_value(f.get("severity", "info"))

    sorted_findings = sorted(findings, key=severity_key)
    return sorted_findings[:top_n]

def compute_requirement_coverage(findings: list[dict], run_dir: Path) -> Optional[float]:
    # Try reading from evaluation.md first
    evaluation_file = run_dir / "evaluation.md"
    if evaluation_file.exists():
        import re
        eval_text = evaluation_file.read_text()
        # Parse "Requirements:** 13/13 implemented" or "Requirements: 12/12 implemented"
        match = re.search(r"Requirements:\*?\*?\s+(\d+)/(\d+)", eval_text)
        if match:
            implemented, total = int(match.group(1)), int(match.group(2))
            return implemented / total if total > 0 else None

    # Fallback: Extract R-numbers from findings
    requirement_kinds = {"requirement_missing", "requirement_partial"}
    missing_partial = sum(1 for f in findings if f.get("kind") in requirement_kinds)

    r_numbers = set()
    for finding in findings:
        fid = finding.get("id", "")
        if fid.startswith("R") and fid[1:].isdigit():
            r_numbers.add(int(fid[1:]))

    if not r_numbers:
        return None

    total_requirements = max(r_numbers)
    if total_requirements == 0:
        return None

    implemented_count = total_requirements - missing_partial
    return implemented_count / total_requirements

def read_model(run_dir: Path) -> str:
    stack_json = run_dir / "stack.json"
    if stack_json.exists():
        with open(stack_json) as f:
            data = json.load(f)
            return data.get("model") or data.get("agent") or "unknown"

    # Try _meta.json
    meta_json = run_dir / "_meta.json"
    if meta_json.exists():
        with open(meta_json) as f:
            data = json.load(f)
            if "run_config" in data and "model" in data["run_config"]:
                return data["run_config"]["model"]

    return "unknown"

def main():
    run_dir_str, min_severity, dry_run = parse_args()

    # Handle relative path from cwd
    run_dir = Path(run_dir_str)
    if not run_dir.is_absolute():
        run_dir = Path.cwd() / run_dir

    findings_path = run_dir / "findings.jsonl"

    if not findings_path.exists():
        print(f"Error: {findings_path} not found — run evaluate-run first", file=sys.stderr)
        sys.exit(1)

    # Load and process findings
    all_findings = load_findings(findings_path)
    filtered_findings = filter_by_severity(all_findings, min_severity)

    severity_counts = count_severities(filtered_findings)
    penalty_score = compute_penalty_score(severity_counts)
    top_findings = collect_top_findings(filtered_findings, 5)
    requirement_coverage = compute_requirement_coverage(all_findings, run_dir)  # Pass run_dir
    model = read_model(run_dir)

    # Build assessment
    assessment = {
        "severity_counts": severity_counts,
        "penalty_score": round(penalty_score, 4),
        "top_findings": top_findings,
        "requirement_coverage": requirement_coverage,
        "model": model,
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    if dry_run:
        print(json.dumps(assessment, indent=2))
    else:
        # Write atomically
        assessment_path = run_dir / "assessment.json"
        tmp_path = run_dir / "assessment.json.tmp"

        with open(tmp_path, "w") as f:
            json.dump(assessment, f, indent=2)

        tmp_path.rename(assessment_path)

        # Print summary
        print(f"Assessment written to {assessment_path}")
        print(f"  Severity counts: critical={severity_counts['critical']} high={severity_counts['high']} medium={severity_counts['medium']} low={severity_counts['low']} info={severity_counts['info']}")
        print(f"  Penalty score:   {penalty_score:.4f}  (1.0 = clean, 0.0 = critical failures)")

        if requirement_coverage is not None:
            print(f"  Req coverage:    {requirement_coverage * 100:.1f}%")
        else:
            print(f"  Req coverage:    unknown")

        print(f"  Model:           {model}")

        if top_findings:
            top = top_findings[0]
            severity = top.get("severity", "unknown").upper()
            title = top.get("title", "")
            print(f"  Top finding:     [{severity.lower()}] {title}")

if __name__ == "__main__":
    main()
