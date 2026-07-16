"""
Optimal-stack selection — generate the data-driven tables in optimal-blog.md
straight from master.db. Exposed as `retort report optimal`.

WHY THIS IS NOT A ONE-LINE "GROUP BY model":
master.db records each run's *scores* but not the full *stack/config* that produced
them. Two gaps in the data pipeline shape this whole script (run with --health to see
them reported against the live db):

  1. LOCAL RUNS HAVE A BLANK `model` COLUMN. The harness wrote `agent: hermes-local`
     into stack.json but no model, so 250+ local rows carry model=''. The only signal
     for *which* local model produced them is the experiment slug. See LOCAL_STACKS.

  2. THERE ARE NO SAMPLING / CONTEXT COLUMNS. temperature/top_p/top_k/repetition_penalty
     are absent, and max_context_tokens is null on all but one row. So "the qualified
     config" cannot be filtered from the data. The blog's headline numbers are best-
     config picks (e.g. local routine 0.83 is the tuned-sampling experiment-27 alone;
     the all-experiment 35B aggregate is 0.28, dragged down by early mis-configured
     runs). Which experiments represent each featured stack's qualified config is
     therefore CURATED HERE, in FEATURED_STACKS, until the pipeline records it.

Fix those two upstream (write model + sampling + context into every provenance.json and
re-ingest) and the curation below collapses into a plain group-by. Until then this module
is the source of truth for *which rows represent each stack*.

Usage:
    retort report optimal                       # print tables + health to stdout
    retort report optimal --health              # only the data-health report
    retort report optimal --write optimal-blog.md   # splice into GEN markers
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# Repo root, from src/retort/reporting/optimal.py -> reporting -> retort -> src -> root.
REPO = Path(__file__).resolve().parents[3]
DB = REPO / "master.db"

ROUTINE_TASK = "rest-api-crud"
HARD_TASK = "brazil-soccer-mcp"

# Rows we never count toward a headline number: the self-repair second-attempt runs
# (experiment-21) are a different question than "does one unattended run pass".
BASE_FILTER = "coalesce(prompt,'') != 'repair'"

# ---------------------------------------------------------------------------
# CURATION. Each featured stack declares a SQL predicate selecting the rows that
# represent it, and the reliability bar at which it counts as "usable" for the
# per-language table (cloud must be perfect; local buys $0 at a lower bar, reviewed).
# ---------------------------------------------------------------------------
FEATURED_STACKS = [
    {
        "name": "Claude Fable 5",
        "short": "Fable 5",
        "models": ["claude-fable-5"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        "name": "Claude Sonnet 5",
        "short": "Sonnet 5",
        "models": ["sonnet-5"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        # opus-4.8 (exp-15) and claude-opus-4-8 (exp-4/5/6/8) are the same model,
        # logged under two names. The -fast serving variant is a different stack and
        # is deliberately excluded.
        "name": "Claude Opus 4.8",
        "short": "Opus 4.8",
        "models": ["claude-opus-4-8", "opus-4.8"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        "name": "Claude Opus 4.7",
        "short": "Opus 4.7",
        "models": ["claude-opus-4-7"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        # Local Qwen3.6-35B-A3B at the QUALIFIED config only. Routine numbers come from
        # the tuned-sampling experiments (27 sampling-ff, 28 rebaseline); hard numbers
        # from the brazil-35b experiments (25/26). Early local experiments (16-20 etc.)
        # ran at bad configs (temp=1.0, 64/128K, wrong playpen) and are excluded on
        # purpose -- including them would report 0.28, not the tuned 0.83. The
        # NOT LIKE '%Next%' guard keeps the 80B Qwen3-Coder-Next rows (also served under
        # an mlxlocal/ id) out of the 35B stack -- they are their own stack below.
        # exp-35 (35B Rust at context_threshold 0.7) is a DIFFERENT stack (the featured 35B
        # is at the 0.35 default) so it is excluded -- see docs/future-experiments.md exp-35.
        "name": "Qwen3.6-35B-A3B (local, $0)",
        "short": "Qwen 35B local",
        "where": (
            "( experiment LIKE '%sampling%' "
            "OR (model LIKE 'mlxlocal%' AND model NOT LIKE '%Next%') "
            "OR experiment LIKE '%brazil-35b%' ) "
            "AND experiment NOT LIKE '%experiment-35%'"
        ),
        "kind": "local",
        "pass_bar": 0.50,
        "cost_override": 0.0,  # local marginal cost is $0 regardless of logged value
    },
    {
        # Qwen3-Coder-Next 80B at the DEFAULT lcm context_threshold 0.35 (exp-29/30 py/go
        # n=9; exp-31 brazil hard n=6; exp-32 prompt sweep; exp-33 TS). Verdict at 0.35:
        # BEST local Python (1.00) but Go 0.67 / TS 0.33, dragged down by an intermittent
        # 25-min stall, and 0.00 on hard. exp-34 (EXCLUDED here on purpose -- it is a
        # different stack at context_threshold 0.7) showed the stall is a compaction
        # artifact: at 0.7, 0 stalls and Go went 3/3. See docs/future-experiments.md
        # exp-30/31/34; a 0.7 re-baseline is queued before changing the featured numbers.
        "name": "Qwen3-Coder-Next 80B (local, $0)",
        "short": "Qwen 80B local",
        "where": (
            "( experiment LIKE '%experiment-29%' OR model LIKE '%Qwen3-Coder-Next%' ) "
            # exp-34 and exp-36 are the context_threshold=0.7 runs (a different stack);
            # keep them out of the featured 0.35-default numbers. See the stall-fix callout.
            "AND experiment NOT LIKE '%experiment-34%' AND experiment NOT LIKE '%experiment-36%'"
        ),
        "kind": "local",
        "pass_bar": 0.50,
        "cost_override": 0.0,
    },
]

# Raw model strings we knowingly do NOT feature, so --health can tell "expected legacy"
# apart from "unmapped / new, investigate". Blank '' is the local-provenance bug.
KNOWN_NONFEATURED = {
    "": "local runs with blank model (provenance bug)",
    "opus": "legacy bare 'opus' (exp-1/2)",
    "sonnet": "legacy bare 'sonnet' (exp-1/2/13/14)",
    "sonnet-4.6": "superseded by Sonnet 5",
    "claude-opus-4-6": "superseded by Opus 4.7/4.8",
    "opus-4.8-fast": "Opus 4.8 fast serving variant (not featured)",
    "claude-opus-4-8-fast": "Opus 4.8 fast serving variant (not featured)",
    "mlxlocal/Qwen3.6-35B-A3B": "counted under the Qwen 35B local stack (slug/mlxlocal match)",
    "mlxlocal/mlx-community--Qwen3-Coder-Next-4bit": "counted under the Qwen 80B local stack (exp-29)",
}


def q(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def stack_where(s):
    """SQL predicate selecting a stack's rows: explicit `where`, else `model IN (...)`."""
    if "where" in s:
        return s["where"]
    lits = ",".join("'" + m.replace("'", "''") + "'" for m in s["models"])
    return f"model IN ({lits})"


def metrics(conn, where, task, language=None):
    """n, pass-proportion, avg cost, avg seconds for a selection on one task."""
    clause = f"({where}) AND task = ? AND {BASE_FILTER}"
    params = [task]
    if language is not None:
        clause += " AND language = ?"
        params.append(language)
    row = q(
        conn,
        f"""
        SELECT COUNT(*) AS n,
               AVG(CASE WHEN requirement_coverage >= 1.0 THEN 1.0 ELSE 0.0 END) AS pass,
               AVG(cost_usd) AS cost,
               AVG(duration_seconds) AS sec
        FROM runs WHERE {clause}
        """,
        params,
    )[0]
    return {"n": row[0], "pass": row[1], "cost": row[2], "sec": row[3]}


def fmt_pass(m):
    return "—" if not m["n"] else f"{m['pass']:.2f}"


def fmt_cost(stack, m):
    if not m["n"]:
        return "—"
    if "cost_override" in stack:
        return f"${stack['cost_override']:.2f}"
    return f"${m['cost']:.2f}" if m["cost"] is not None else "—"


def fmt_sec(m):
    return "—" if not m["n"] or m["sec"] is None else f"{m['sec']:.0f} s"


# ---------------------------------------------------------------------------
# Table 1: leading stacks (reliability / cost / time, routine vs hard)
# ---------------------------------------------------------------------------
def leading_stacks_table(conn):
    lines = [
        "| Stack | Reliability (routine · hard) | Cost (routine · hard) | Time (routine · hard) |",
        "|---|---:|---:|---:|",
    ]
    for s in FEATURED_STACKS:
        r = metrics(conn, stack_where(s), ROUTINE_TASK)
        h = metrics(conn, stack_where(s), HARD_TASK)
        # Show the measured hard-task number when we have runs; only mark "n/q"
        # when a stack has genuinely never been run on the hard task. (Local
        # stacks used to be blanket-n/q; the 35B has brazil-35b runs and the 80B
        # has exp-31, so those now report real numbers — both poor, which is the
        # point: local models approach but don't reliably clear hard tasks.)
        hard_pass = fmt_pass(h)
        hard_cost = fmt_cost(s, h)
        hard_sec = fmt_sec(h)
        lines.append(
            f"| **{s['name']}** | {fmt_pass(r)} · {hard_pass} "
            f"| {fmt_cost(s, r)} · {hard_cost} "
            f"| {fmt_sec(r)} · {hard_sec} |"
        )
    return "\n".join(lines)


def routine_languages(conn):
    return [
        r[0]
        for r in q(
            conn,
            f"SELECT DISTINCT language FROM runs WHERE task = ? AND language IS NOT NULL "
            f"AND {BASE_FILTER} ORDER BY language",
            (ROUTINE_TASK,),
        )
    ]


# ---------------------------------------------------------------------------
# Table 2 (the centrepiece): per-language SUCCESS RATE matrix.
# A single cross-language aggregate is misleading -- it blends a stack's strong
# languages with its weak ones (e.g. local Qwen passes Python/Go but fails Rust,
# so its "overall" number is neither). Report the pass rate per (language, stack)
# instead, so a weak language can't hide inside a good average. Cells: pass (n).
# ---------------------------------------------------------------------------
def per_language_matrix(conn):
    langs = routine_languages(conn)
    header = "| Language | " + " | ".join(s["short"] for s in FEATURED_STACKS) + " |"
    sep = "|---|" + "".join("---:|" for _ in FEATURED_STACKS)
    lines = [header, sep]
    for lang in langs:
        cells = []
        for s in FEATURED_STACKS:
            m = metrics(conn, stack_where(s), ROUTINE_TASK, language=lang)
            cells.append("—" if not m["n"] else f"{m['pass']:.2f} ({m['n']})")
        lines.append(f"| **{lang}** | " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table 3: per-language routine — cheapest stack that clears its bar
# ---------------------------------------------------------------------------
def per_language_table(conn):
    langs = routine_languages(conn)
    lines = [
        "| Language | Routine → cheapest qualifying stack | Reliability | n |",
        "|---|---|---:|---:|",
    ]
    for lang in langs:
        candidates = []
        for s in FEATURED_STACKS:
            m = metrics(conn, stack_where(s), ROUTINE_TASK, language=lang)
            if m["n"] and m["pass"] >= s["pass_bar"]:
                cost = s.get("cost_override", m["cost"] if m["cost"] is not None else 1e9)
                candidates.append((cost, s, m))
        if not candidates:
            lines.append(f"| **{lang}** | *no qualifying stack in db* | — | — |")
            continue
        candidates.sort(key=lambda c: c[0])
        cost, s, m = candidates[0]
        cost_str = "$0" if s.get("cost_override") == 0.0 else f"${m['cost']:.2f}"
        lines.append(
            f"| **{lang}** | {s['name']} ({cost_str}) | {m['pass']:.2f} | {m['n']} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table 3: prompt / testing method — the prompt-factor sweep on the local models.
# The lever bites on a WEAK model (35B: ATDD tanks) and flattens to a no-op on a
# STRONG one (80B: every prompt passes) -- the same way it is a flat line on cloud.
# ---------------------------------------------------------------------------
def prompt_method_table(conn):
    def sweep(where):
        return {
            p: (n, pa)
            for p, n, pa in q(
                conn,
                f"SELECT prompt, COUNT(*), "
                f"AVG(CASE WHEN requirement_coverage >= 1.0 THEN 1.0 ELSE 0.0 END) "
                f"FROM runs WHERE {where} GROUP BY prompt",
            )
        }

    m35 = sweep("experiment LIKE '%hermes35b-prompts%'")   # exp-19, weak local model
    m80 = sweep("experiment LIKE '%prompts-80b%'")          # exp-32, strong local model
    if not m35 and not m80:
        return "*(no local prompt-sweep experiment found)*"
    lines = [
        "| Prompt | 35B pass | 80B pass |",
        "|---|---:|---:|",
    ]
    for p in ("neutral", "BDD", "TDD", "ATDD"):
        c35 = f"{m35[p][1]:.2f} (n={m35[p][0]})" if p in m35 else "—"
        c80 = f"{m80[p][1]:.2f} (n={m80[p][0]})" if p in m80 else "—"
        lines.append(f"| **{p}** | {c35} | {c80} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Data-health report — answers "is it all in master.db, and is anything broken?"
# ---------------------------------------------------------------------------
def health_report(conn, repo_root: Path = REPO):
    out = ["## Data health\n"]

    # 1. missing config columns
    cols = {r[1] for r in q(conn, "PRAGMA table_info(runs)")}
    missing = [c for c in ("temperature", "top_p", "top_k", "repetition_penalty") if c not in cols]
    if missing:
        out.append(
            f"- ⚠️ **No sampling columns** ({', '.join(missing)}). The qualified config "
            f"cannot be verified from the db — it is curated in FEATURED_STACKS."
        )
    ctx_populated = q(conn, "SELECT COUNT(*) FROM runs WHERE coalesce(max_context_tokens,0) > 0")[0][0]
    total = q(conn, "SELECT COUNT(*) FROM runs")[0][0]
    out.append(f"- ⚠️ **max_context_tokens populated on {ctx_populated}/{total} rows** — cannot filter by context window.")

    # 2. blank-model local rows
    blank = q(
        conn,
        "SELECT COUNT(*), group_concat(DISTINCT experiment) FROM runs WHERE trim(coalesce(model,'')) = ''",
    )[0]
    if blank[0]:
        out.append(
            f"- ⚠️ **{blank[0]} rows have a blank model** (local provenance bug). "
            f"Attributed to stacks via experiment slug. Experiments: {blank[1]}"
        )

    # 3. unmapped / unexpected model strings
    featured_raw = set()
    for s in FEATURED_STACKS:
        featured_raw |= set(s.get("models", []))
    seen = {r[0] for r in q(conn, "SELECT DISTINCT coalesce(model,'') FROM runs")}
    unmapped = sorted(m for m in seen if m not in featured_raw and m not in KNOWN_NONFEATURED)
    if unmapped:
        out.append(f"- ⚠️ **Unmapped model strings** (new? investigate): {unmapped}")
    else:
        out.append("- ✅ Every model string is either featured or a known non-featured/legacy label.")

    # 4. experiment dirs on disk not present in the db
    db_exps = {r[0] for r in q(conn, "SELECT DISTINCT experiment FROM runs")}
    db_nums = {_expnum(e) for e in db_exps}
    experiments_dir = repo_root / "experiments"
    disk = sorted(
        p.name for p in experiments_dir.glob("*/experiment-*") if p.is_dir()
    ) if experiments_dir.exists() else []
    orphans = [d for d in disk if _expnum(d) not in db_nums]
    if orphans:
        out.append(f"- ⚠️ **Experiment dirs on disk but NOT in master.db:** {sorted(set(orphans))}")
    elif disk:
        out.append("- ✅ Every experiment directory on disk appears in master.db.")

    return "\n".join(out)


def _expnum(slug: str):
    """experiment-16-qwen3coder-bookshop -> 16 (for matching dir<->db)."""
    parts = slug.split("-")
    for p in parts[1:]:
        if p.isdigit():
            return int(p)
    return None


def render_all(conn, repo_root: Path = REPO):
    return "\n\n".join(
        [
            "### Leading stacks\n\n" + leading_stacks_table(conn),
            "### Per-language success rate — pass (n)\n\n" + per_language_matrix(conn),
            "### Per language (routine) — cheapest qualifying\n\n" + per_language_table(conn),
            "### Prompt / testing method — local sweep\n\n" + prompt_method_table(conn),
            health_report(conn, repo_root),
        ]
    )


def splice(path: Path, conn) -> tuple[int, list[str]]:
    """Replace regions between <!-- GEN:<key> START/END --> markers with fresh
    tables. Returns ``(n_spliced, skipped_keys)`` — the caller decides how to
    report; nothing is printed here so this stays usable as a library call.
    """
    blocks = {
        "leading-stacks": leading_stacks_table(conn),
        "per-language-matrix": per_language_matrix(conn),
        "per-language": per_language_table(conn),
        "prompt-method": prompt_method_table(conn),
    }
    text = path.read_text()
    changed = 0
    skipped: list[str] = []
    for key, table in blocks.items():
        start = f"<!-- GEN:{key} START -->"
        end = f"<!-- GEN:{key} END -->"
        if start not in text or end not in text:
            skipped.append(key)
            continue
        pre, rest = text.split(start, 1)
        _, post = rest.split(end, 1)
        text = f"{pre}{start}\n{table}\n{end}{post}"
        changed += 1
    path.write_text(text)
    return changed, skipped


def open_db(db_path: str | Path = DB) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))
