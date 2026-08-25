#!/bin/bash
set -eo pipefail

# file-run-issues: Aggregate findings.jsonl into assessment.json

usage() {
    echo "Usage: $0 --run-dir <path> [--min-severity <level>] [--dry-run]" >&2
    exit 1
}

# Defaults
run_dir=""
min_severity="info"
dry_run=false

# Parse flags
while [[ $# -gt 0 ]]; do
    case $1 in
        --run-dir) run_dir="$2"; shift 2 ;;
        --min-severity) min_severity="$2"; shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        *) usage ;;
    esac
done

[[ -z "$run_dir" ]] && usage

# Severity rank lookup
get_severity_rank() {
    case "$1" in
        critical) echo 4 ;;
        high) echo 3 ;;
        medium) echo 2 ;;
        low) echo 1 ;;
        info) echo 0 ;;
        *) echo -1 ;;
    esac
}

min_rank=$(get_severity_rank "$min_severity")
if [[ $min_rank -eq -1 ]]; then
    echo "Invalid severity: $min_severity" >&2
    exit 1
fi

# Initialize severity counts
critical_count=0
high_count=0
medium_count=0
low_count=0
info_count=0

# Load findings.jsonl
findings_file="$run_dir/findings.jsonl"

# Temporary file for filtered findings
filtered_findings=$(mktemp)
trap "rm -f $filtered_findings" EXIT

max_r_number=0
requirement_missing_count=0
requirement_partial_count=0

# Read findings line by line if file exists
if [[ -f "$findings_file" ]]; then
    while IFS= read -r line; do
        # Parse JSON fields
        id=$(echo "$line" | jq -r '.id // empty' 2>/dev/null || echo "")
        severity=$(echo "$line" | jq -r '.severity // "info"' 2>/dev/null || echo "info")
        kind=$(echo "$line" | jq -r '.kind // empty' 2>/dev/null || echo "")

        # Extract R-number from ID (e.g., "R3" -> 3)
        if [[ $id =~ ^R([0-9]+)$ ]]; then
            r_num="${BASH_REMATCH[1]}"
            if (( r_num > max_r_number )); then
                max_r_number=$r_num
            fi
        fi

        # Count requirement issues
        if [[ "$kind" == "requirement_missing" ]]; then
            ((requirement_missing_count++))
        elif [[ "$kind" == "requirement_partial" ]]; then
            ((requirement_partial_count++))
        fi

        # Filter by severity and add to counts
        sev_rank=$(get_severity_rank "$severity")
        if (( sev_rank >= min_rank )); then
            case "$severity" in
                critical) ((critical_count++)) ;;
                high) ((high_count++)) ;;
                medium) ((medium_count++)) ;;
                low) ((low_count++)) ;;
                info) ((info_count++)) ;;
            esac
            echo "$line" >> "$filtered_findings"
        fi
    done < "$findings_file"
fi

# Select top 5 findings by severity (preserving order within each severity level)
top_findings_json="["
first=true
count=0

for target_sev in critical high medium low info; do
    if (( count >= 5 )); then
        break
    fi

    if [[ -f "$filtered_findings" ]]; then
        while IFS= read -r line; do
            if (( count >= 5 )); then
                break
            fi
            line_sev=$(echo "$line" | jq -r '.severity // "info"' 2>/dev/null || echo "info")
            if [[ "$line_sev" == "$target_sev" ]]; then
                if [[ $first == true ]]; then
                    first=false
                else
                    top_findings_json+=","
                fi
                top_findings_json+="$line"
                ((count++))
            fi
        done < "$filtered_findings"
    fi
done

top_findings_json+="]"

# Compute penalty score
penalty_critical=$(echo "${critical_count} * 0.25" | bc -l)
penalty_high=$(echo "${high_count} * 0.10" | bc -l)
penalty_medium=$(echo "${medium_count} * 0.03" | bc -l)
penalty_low=$(echo "${low_count} * 0.01" | bc -l)

total_penalty=$(echo "$penalty_critical + $penalty_high + $penalty_medium + $penalty_low" | bc -l)
penalty_score=$(echo "1.0 - $total_penalty" | bc -l)

# Clamp to [0.0, 1.0]
if (( $(echo "$penalty_score < 0" | bc -l) )); then
    penalty_score="0.0"
elif (( $(echo "$penalty_score > 1" | bc -l) )); then
    penalty_score="1.0"
fi

# Round to 4 decimal places
penalty_score=$(printf "%.4f" "$penalty_score")

# Compute requirement coverage
requirement_coverage="null"
if (( max_r_number > 0 )); then
    implemented_count=$((max_r_number - requirement_missing_count - requirement_partial_count))
    if (( implemented_count < 0 )); then
        implemented_count=0
    fi
    coverage_decimal=$(echo "scale=4; $implemented_count / $max_r_number" | bc -l)
    requirement_coverage="$coverage_decimal"
fi

# Get model from stack.json
model="unknown"
stack_file="$run_dir/stack.json"
if [[ -f "$stack_file" ]]; then
    model=$(jq -r '.model // .agent // "unknown"' "$stack_file" 2>/dev/null || echo "unknown")
fi

# Get evaluated_at timestamp (ISO 8601 UTC)
evaluated_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build the assessment JSON
if [[ "$requirement_coverage" == "null" ]]; then
    requirement_coverage_json="null"
else
    requirement_coverage_json="$requirement_coverage"
fi

assessment_json=$(cat <<EOF
{
  "severity_counts": {
    "critical": $critical_count,
    "high": $high_count,
    "medium": $medium_count,
    "low": $low_count,
    "info": $info_count
  },
  "penalty_score": $penalty_score,
  "top_findings": $top_findings_json,
  "requirement_coverage": $requirement_coverage_json,
  "model": "$model",
  "evaluated_at": "$evaluated_at"
}
EOF
)

# Prettify JSON
assessment_json=$(echo "$assessment_json" | jq .)

# Handle dry-run
if [[ $dry_run == true ]]; then
    echo "$assessment_json"
else
    # Write atomically via temp file
    tmp_file="$run_dir/assessment.json.tmp"
    final_file="$run_dir/assessment.json"

    echo "$assessment_json" > "$tmp_file"
    if ! mv "$tmp_file" "$final_file" 2>/dev/null; then
        # Fall back to direct write if rename fails
        echo "$assessment_json" > "$final_file"
        echo "Warning: atomic rename failed, fell back to direct write" >&2
    fi

    # Print summary
    echo "Assessment written to $final_file"
    echo "  Severity counts: critical=$critical_count high=$high_count medium=$medium_count low=$low_count info=$info_count"
    echo "  Penalty score:   $penalty_score  (1.0 = clean, 0.0 = critical failures)"

    if [[ "$requirement_coverage" != "null" ]]; then
        coverage_pct=$(echo "scale=1; $requirement_coverage * 100" | bc)
        echo "  Req coverage:    $coverage_pct%"
    else
        echo "  Req coverage:    unknown"
    fi

    echo "  Model:           $model"

    # Print top finding if exists
    if [[ -f "$filtered_findings" ]]; then
        top_finding=$(head -1 "$filtered_findings")
        if [[ -n "$top_finding" ]]; then
            top_sev=$(echo "$top_finding" | jq -r '.severity // "info"')
            top_title=$(echo "$top_finding" | jq -r '.title // "(no title)"')
            echo "  Top finding:     [$top_sev] $top_title"
        fi
    fi
fi
