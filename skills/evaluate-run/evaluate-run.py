#!/usr/bin/env python3
"""
Evaluate a retort experiment run against task requirements.
Produces evaluation.md and findings.jsonl.
"""

import json
import sys
import argparse
import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import tempfile
import shutil
import os

def run_command(cmd, timeout=120, cwd=None, capture=True):
    """Run command and return (exit_code, stdout, stderr, duration)"""
    try:
        start = datetime.now()
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=capture,
            timeout=timeout,
            cwd=cwd,
            text=True
        )
        duration = (datetime.now() - start).total_seconds()
        return (result.returncode, result.stdout, result.stderr, duration)
    except subprocess.TimeoutExpired:
        return (124, "", "TIMEOUT", timeout)
    except Exception as e:
        return (1, "", str(e), 0)

def detect_language(stack_json_path):
    """Detect language from stack.json"""
    try:
        with open(stack_json_path) as f:
            data = json.load(f)
            return data.get("language", "unknown")
    except:
        return "unknown"

def extract_requirements_from_task(task_md_path):
    """Extract requirements from TASK.md into a list of (id, text) tuples"""
    if not task_md_path.exists():
        return []

    requirements = []
    content = task_md_path.read_text()

    # Look for numbered lists (1. 2. 3.)
    numbered_pattern = r'^\d+\.\s+(.+?)(?=\n\d+\.|$)'
    for match in re.finditer(numbered_pattern, content, re.MULTILINE | re.DOTALL):
        text = match.group(1).strip()
        # Take first line if multi-line
        text = text.split('\n')[0].strip()
        if text:
            requirements.append((f"R{len(requirements) + 1}", text))

    # If no numbered requirements, look for bullet points starting with "must" or "should"
    if not requirements:
        bullet_pattern = r'^\s*[-*]\s+(.+?)$'
        for match in re.finditer(bullet_pattern, content, re.MULTILINE):
            text = match.group(1).strip()
            if text.lower().startswith(('must', 'should')):
                requirements.append((f"R{len(requirements) + 1}", text))

    return requirements

def get_build_command(language):
    """Return appropriate build command for language"""
    commands = {
        "typescript": "npm install --no-audit --no-fund && npm run build",
        "python": "python -m py_compile **/*.py",
        "go": "go build ./...",
        "rust": "cargo build --quiet"
    }
    return commands.get(language, f"# Unknown language: {language}")

def get_test_command(language):
    """Return appropriate test command for language"""
    commands = {
        "typescript": "npm test --silent",
        "python": "pytest -q",
        "go": "go test ./...",
        "rust": "cargo test --quiet"
    }
    return commands.get(language, f"# Unknown language: {language}")

def get_lint_command(language):
    """Return appropriate lint command for language"""
    commands = {
        "typescript": "npm run lint",
        "python": "ruff check .",
        "go": "go vet ./...",
        "rust": "cargo clippy -- -D warnings"
    }
    return commands.get(language, f"# Unknown language: {language}")

def run_build(run_dir, language):
    """Build the project"""
    cmd = get_build_command(language)
    exit_code, stdout, stderr, duration = run_command(cmd, timeout=120, cwd=run_dir)
    return {
        "status": "pass" if exit_code == 0 else "fail" if exit_code != 124 else "unavailable",
        "exit_code": exit_code,
        "stdout": stdout[:2000] if stdout else "",
        "stderr": stderr[:2000] if stderr else "",
        "duration": duration,
        "command": cmd
    }

def run_tests(run_dir, language):
    """Run tests for the project"""
    cmd = get_test_command(language)
    exit_code, stdout, stderr, duration = run_command(cmd, timeout=180, cwd=run_dir)

    # Parse test results if possible
    passed = failed = skipped = 0
    output = stdout + stderr

    # Simple patterns to extract test counts
    if "passed" in output.lower():
        match = re.search(r'(\d+)\s+passed', output, re.IGNORECASE)
        if match:
            passed = int(match.group(1))
    if "failed" in output.lower():
        match = re.search(r'(\d+)\s+failed', output, re.IGNORECASE)
        if match:
            failed = int(match.group(1))
    if "skipped" in output.lower():
        match = re.search(r'(\d+)\s+skipped', output, re.IGNORECASE)
        if match:
            skipped = int(match.group(1))

    return {
        "status": "pass" if exit_code == 0 else "fail" if exit_code != 124 else "unavailable",
        "exit_code": exit_code,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "effective": passed + failed,
        "stdout": stdout[:2000] if stdout else "",
        "stderr": stderr[:2000] if stderr else "",
        "duration": duration,
        "command": cmd
    }

def run_lint(run_dir, language):
    """Run linter for the project"""
    cmd = get_lint_command(language)
    exit_code, stdout, stderr, duration = run_command(cmd, timeout=60, cwd=run_dir)

    # Count warnings
    output = stdout + stderr
    warning_count = len(re.findall(r'warning|warn', output, re.IGNORECASE))

    return {
        "status": "pass" if exit_code == 0 else "fail" if exit_code != 124 else "unavailable",
        "exit_code": exit_code,
        "warning_count": warning_count,
        "stdout": stdout[:1500] if stdout else "",
        "stderr": stderr[:1500] if stderr else "",
        "duration": duration,
        "command": cmd
    }

def count_skipped_tests(run_dir, language):
    """Count skipped/disabled tests"""
    patterns = {
        "python": r"pytest\.skip|@pytest\.mark\.skip|xfail",
        "typescript": r"\.skip\(|xit\(|xdescribe\(|it\.todo\(",
        "go": r"t\.Skip\(|t\.Skipf\(",
        "rust": r"#\[ignore\]|#\[cfg\(ignore\)\]"
    }

    pattern = patterns.get(language)
    if not pattern:
        return 0

    count = 0
    for root, dirs, files in os.walk(run_dir):
        # Skip build directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', 'target', '__pycache__', '.git']]

        extensions = {
            "python": [".py"],
            "typescript": [".ts", ".js"],
            "go": [".go"],
            "rust": [".rs"]
        }

        for file in files:
            if any(file.endswith(ext) for ext in extensions.get(language, [])):
                try:
                    content = Path(root) / file
                    text = content.read_text()
                    matches = len(re.findall(pattern, text))
                    count += matches
                except:
                    pass

    return count

def assess_requirements(run_dir, requirements, build_result, test_result, source_files):
    """Assess each requirement against the codebase"""
    assessments = []

    for req_id, req_text in requirements:
        # Simple heuristic: search for keywords in source files
        keywords = req_text.lower().split()
        found = False
        evidence = ""

        for source_file in source_files:
            try:
                content = source_file.read_text().lower()
                if all(kw in content for kw in keywords[:2]):  # Check first 2 keywords
                    found = True
                    evidence = str(source_file.relative_to(run_dir))
                    break
            except:
                pass

        if build_result["status"] == "fail":
            status = "cannot-verify"
            evidence = f"Build failed: {build_result['stderr'][:100]}"
        elif test_result["status"] == "fail":
            status = "cannot-verify" if not found else "partial"
            evidence = evidence or f"Tests failed; {test_result['failed']} failures"
        elif found:
            status = "implemented"
        else:
            status = "missing"
            evidence = "No matching code found"

        assessments.append({
            "id": req_id,
            "requirement": req_text,
            "status": status,
            "evidence": evidence
        })

    return assessments

def compute_metrics(run_dir, language):
    """Compute metrics about the codebase"""
    # Count lines of code
    extensions = {
        "python": [".py"],
        "typescript": [".ts", ".js", ".tsx", ".jsx"],
        "go": [".go"],
        "rust": [".rs"]
    }

    ext_list = extensions.get(language, [])
    loc = 0
    file_count = 0
    dep_count = 0

    for root, dirs, files in os.walk(run_dir):
        dirs[:] = [d for d in dirs if d not in ['node_modules', 'target', '__pycache__', '.git', 'dist', 'build']]

        for file in files:
            if any(file.endswith(ext) for ext in ext_list):
                file_count += 1
                try:
                    path = Path(root) / file
                    loc += len(path.read_text().splitlines())
                except:
                    pass

    # Count dependencies
    if language == "typescript" and (run_dir / "package.json").exists():
        try:
            with open(run_dir / "package.json") as f:
                data = json.load(f)
                dep_count = len(data.get("dependencies", {})) + len(data.get("devDependencies", {}))
        except:
            pass
    elif language == "python" and (run_dir / "requirements.txt").exists():
        try:
            dep_count = len((run_dir / "requirements.txt").read_text().strip().splitlines())
        except:
            pass

    return {
        "lines_of_code": loc,
        "files": file_count,
        "dependencies": dep_count
    }

def write_findings(findings, output_path):
    """Write findings to findings.jsonl"""
    with open(output_path, 'w') as f:
        for finding in findings:
            f.write(json.dumps(finding) + '\n')

def write_evaluation(run_dir, assessment_data, output_path):
    """Write human-readable evaluation report"""
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    report = []
    report.append(f"# Evaluation Report")
    report.append("")
    report.append(f"Generated: {timestamp}")
    report.append("")

    # Summary section
    report.append("## Summary")
    report.append("")
    report.append(f"- **Language:** {assessment_data['language']}")
    report.append(f"- **Status:** {assessment_data['status']}")

    build = assessment_data['build']
    report.append(f"- **Build:** {build['status']} ({build['duration']:.1f}s)")

    test = assessment_data['test']
    report.append(f"- **Tests:** {test['passed']} passed, {test['failed']} failed, {test['skipped']} skipped")

    lint = assessment_data['lint']
    report.append(f"- **Lint:** {lint['status']} ({lint['warning_count']} warnings)")

    report.append("")

    # Requirements section
    if assessment_data['requirements']:
        report.append("## Requirements")
        report.append("")
        report.append("| ID | Requirement | Status | Evidence |")
        report.append("|----|----|----|----|")

        for req in assessment_data['requirements']:
            status_icon = {
                "implemented": "✓",
                "partial": "~",
                "missing": "✗",
                "cannot-verify": "?"
            }.get(req['status'], '?')

            report.append(f"| {req['id']} | {req['requirement'][:50]} | {status_icon} {req['status']} | {req['evidence'][:40]} |")

        report.append("")

    # Build & Test section
    report.append("## Build & Test")
    report.append("")
    report.append("### Build")
    report.append(f"```")
    report.append(f"Command: {build['command']}")
    report.append(f"Exit code: {build['exit_code']}")
    if build['stdout']:
        report.append(build['stdout'][:1000])
    if build['stderr']:
        report.append(build['stderr'][:1000])
    report.append("```")
    report.append("")

    report.append("### Tests")
    report.append(f"```")
    report.append(f"Command: {test['command']}")
    report.append(f"Exit code: {test['exit_code']}")
    report.append(f"Results: {test['passed']} passed, {test['failed']} failed, {test['skipped']} skipped")
    if test['stdout']:
        report.append(test['stdout'][:1000])
    report.append("```")
    report.append("")

    # Metrics section
    report.append("## Metrics")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")

    metrics = assessment_data['metrics']
    report.append(f"| Lines of code | {metrics['lines_of_code']} |")
    report.append(f"| Files | {metrics['files']} |")
    report.append(f"| Dependencies | {metrics['dependencies']} |")
    report.append(f"| Tests effective | {test['effective']} |")
    report.append(f"| Skip ratio | {100 * test['skipped'] / max(1, test['effective']):.1f}% |")

    report.append("")

    # Reproduce section
    report.append("## Reproduce")
    report.append("")
    report.append("```bash")
    report.append(f"cd {run_dir}")
    report.append(f"npm install  # or equivalent for your language")
    report.append(f"npm run build")
    report.append(f"npm test")
    report.append("```")

    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

def main():
    parser = argparse.ArgumentParser(description="Evaluate a retort experiment run")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--output-file", help="Path for evaluation.md (default: {run_dir}/evaluation.md)")
    parser.add_argument("--findings-file", help="Path for findings.jsonl (default: {run_dir}/findings.jsonl)")

    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run_dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Verify workspace structure
    task_md = run_dir / "TASK.md"
    stack_json = run_dir / "stack.json"

    if not task_md.exists() or not stack_json.exists():
        print(f"Error: TASK.md or stack.json missing in {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Detect language
    language = detect_language(stack_json)

    # Extract requirements
    requirements = extract_requirements_from_task(task_md)

    # Run build, test, lint
    build_result = run_build(run_dir, language)
    test_result = run_tests(run_dir, language)
    lint_result = run_lint(run_dir, language)

    # Count skipped tests
    skipped_count = count_skipped_tests(run_dir, language)
    test_result["skipped"] = skipped_count

    # Get source files for assessment
    extensions = {
        "python": [".py"],
        "typescript": [".ts", ".js", ".tsx", ".jsx"],
        "go": [".go"],
        "rust": [".rs"]
    }

    source_files = []
    for ext in extensions.get(language, []):
        source_files.extend(run_dir.glob(f"**/*{ext}"))

    # Assess requirements
    assessments = assess_requirements(run_dir, requirements, build_result, test_result, source_files)

    # Compute metrics
    metrics = compute_metrics(run_dir, language)

    # Build findings list
    findings = []

    # Add requirement findings
    for assessment in assessments:
        if assessment['status'] == 'missing':
            findings.append({
                "id": assessment['id'],
                "kind": "requirement_missing",
                "severity": "high",
                "title": f"Requirement not implemented: {assessment['requirement']}",
                "evidence": assessment['evidence'],
                "suggestion": "Implement this requirement"
            })
        elif assessment['status'] == 'partial':
            findings.append({
                "id": assessment['id'],
                "kind": "requirement_partial",
                "severity": "medium",
                "title": f"Requirement incomplete: {assessment['requirement']}",
                "evidence": assessment['evidence'],
                "suggestion": "Complete the implementation"
            })

    # Add build/test findings
    if build_result['status'] == 'fail':
        findings.append({
            "id": "build-fail",
            "kind": "build_failure",
            "severity": "critical",
            "title": "Build failed",
            "evidence": f"{build_result['command']} exited with code {build_result['exit_code']}",
            "suggestion": "Fix build errors before running tests"
        })

    if test_result['status'] == 'fail':
        findings.append({
            "id": "test-fail",
            "kind": "test_failure",
            "severity": "high",
            "title": f"Tests failed: {test_result['failed']} failures",
            "evidence": f"{test_result['command']} returned {test_result['failed']} failures",
            "suggestion": "Fix failing tests"
        })

    # Add skipped test findings
    if test_result['skipped'] > 0:
        findings.append({
            "id": "skipped-tests",
            "kind": "skipped_test",
            "severity": "medium",
            "title": f"{test_result['skipped']} tests are skipped",
            "evidence": f"Skipped test count: {test_result['skipped']}",
            "suggestion": "Implement or remove skipped tests"
        })

    if lint_result['status'] == 'fail' and lint_result['warning_count'] > 0:
        findings.append({
            "id": "lint-warnings",
            "kind": "lint_warning",
            "severity": "low",
            "title": f"{lint_result['warning_count']} lint warnings",
            "evidence": f"Linter found {lint_result['warning_count']} issues",
            "suggestion": "Address lint warnings"
        })

    # Determine overall status
    status = "ok"
    if build_result['status'] == 'fail':
        status = "failed (build)"
    elif test_result['status'] == 'fail':
        status = "failed (tests)"
    elif build_result['status'] == 'unavailable' or test_result['status'] == 'unavailable':
        status = "cannot-verify (toolchain missing)"

    # Write findings file
    findings_path = Path(args.findings_file or str(run_dir / "findings.jsonl"))
    write_findings(findings, findings_path)
    print(f"Wrote findings to {findings_path}")

    # Prepare assessment data for report
    assessment_data = {
        "language": language,
        "status": status,
        "build": build_result,
        "test": test_result,
        "lint": lint_result,
        "requirements": assessments,
        "metrics": metrics
    }

    # Write evaluation report
    output_path = Path(args.output_file or str(run_dir / "evaluation.md"))
    write_evaluation(run_dir, assessment_data, output_path)
    print(f"Wrote evaluation to {output_path}")

if __name__ == "__main__":
    main()
