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
# per-language table. THE BAR IS 1.00 FOR EVERY STACK, local and cloud alike —
# the metric is "the probability a single unattended run is completely correct",
# and a stack being free is already expressed in the cost column, not by lowering
# the standard it is measured against.
# ---------------------------------------------------------------------------
FEATURED_STACKS = [
    {
        # exp-46: 26/26 — every one of the 13 languages on BOTH tasks, the only
        # model that clears the hard task everywhere. Listed first because it is
        # the broadest-coverage stack; the cheapest-qualifying logic still prefers
        # Fable 5 / 4.8 wherever they qualify, which is the point.
        "name": "Claude Opus 5",
        "short": "Opus 5",
        "models": ["claude-opus-5"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        "name": "Claude Fable 5",
        "short": "Fable 5",
        "models": ["claude-fable-5"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        # OpenAI's GPT-5.6 tiers, driven by `codex exec`. Priced onto the Claude
        # ladder rather than against it: Luna<->Sonnet, Terra<->Opus, Sol<->Fable.
        # Cost for these is COMPUTED at list price per token (retort.pricing) —
        # a ChatGPT subscription reports none, and recording $0 would have made
        # them win every cheapest-qualifying route on an unmeasured number.
        "name": "GPT-5.6 Terra (codex)",
        "short": "Terra",
        "models": ["gpt-5.6-terra"],
        "kind": "cloud",
        "pass_bar": 1.00,
    },
    {
        "name": "GPT-5.6 Luna (codex)",
        "short": "Luna",
        "models": ["gpt-5.6-luna"],
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
        # exp-35 (35B Rust at context_threshold 0.7) is a DIFFERENT stack (the featured 35B
        # is at the 0.35 default) so it is excluded -- see docs/past-experiments.md exp-35.
        #
        # The model clause is a POSITIVE match on the 35B's id. It used to be
        # "mlxlocal% AND NOT %Next%", i.e. "any local model except the 80B" -- which
        # silently adopted every NEW local model into the 35B's numbers. exp-47 landed
        # 15 gpt-oss-20b runs and they were counted as 35B, moving published per-language
        # figures (go 0.87->0.84, python 0.80->0.78, ts 0.33->0.38) before the extra rows
        # gave it away. Never enumerate local stacks by exclusion; match the model.
        # The two experiment LIKE clauses stay because exp-25/26/27 predate model
        # recording (model IS NULL on all 60 rows) -- verified 35B-only experiments.
        "name": "Qwen3.6-35B-A3B (local, $0)",
        "short": "Qwen 35B local",
        "where": (
            "( experiment LIKE '%sampling%' "
            "OR model LIKE '%Qwen3.6-35B%' "
            "OR experiment LIKE '%brazil-35b%' ) "
            "AND experiment NOT LIKE '%experiment-35%'"
        ),
        "kind": "local",
        # ONE BAR FOR EVERYONE. This was 0.50 for local stacks on the reasoning
        # that a $0 stack is worth a lower bar if you are watching it. That
        # contradicted this document's own definition of the metric — "the
        # probability a single UNATTENDED run comes out completely correct", where
        # "a single sub-1.0 run is a fail" — and it let a coin flip outrank a
        # perfect stack purely on price: python-on-hard-task recommended the local
        # 35B at 0.50. Being free is already represented, in the cost column.
        # Holding local to 1.00 did not remove local from the recommendations; it
        # switched routine python/go from the 35B (0.85/0.87) to the 80B (1.00),
        # still at $0. The double standard was hiding the better local stack.
        "pass_bar": 1.00,
        "cost_override": 0.0,  # local marginal cost is $0 regardless of logged value
        # Headline aggregate scoped to the languages this stack is RECOMMENDED for
        # (python/go). Rust (0.00) and TS (0.00) failed here and go to cloud; leaving
        # them in the aggregate would understate the stack on the work it's actually
        # for. The per-language matrix stays unscoped and shows those 0.00s in full.
        "routine_scope": ["python", "go"],
    },
    {
        # Qwen3-Coder-Next 80B at the RECOMMENDED lcm context_threshold 0.9 ("full context").
        # exp-38 is the clean full-9-language baseline at 0.9 (n=3/language, one experiment):
        #   routine  -> python 3/3, go 3/3, TYPESCRIPT 3/3 (all 1.00) -- TS is the unlock: it
        #               was 0.33 at ctx 0.35/0.7, and full context makes it reliable.
        #               rust 1/3 (rep2/rep3 are near-misses 0.92/0.83 -- their archived code
        #               compiles and tests pass 100%, they just miss 1-2 spec reqs; NOT stalls,
        #               confirmed via `retort diagnose`+`rescore`+`reevaluate`. Rust -> cloud.
        #               java/erlang 0/3 near-misses; clojure/csharp/elixir 0/3 GENUINE all-zeros
        #               (cannot produce working code). Niche languages -> cloud.
        #   hard     -> exp-39 (brazil at the SAME 0.9 config, 0/6) -- config-INVARIANT is now
        #               VERIFIED, not assumed: exp-31 was 0/6 at 0.7, exp-39 is 0/6 at 0.9, so
        #               full context doesn't crack the hard task (python best 11/12; go actually
        #               regressed via a stall -- the late-compaction downside on a non-finishing
        #               run). Hard column uses exp-39 for 0.9 config-purity (exp-38 ran no hard).
        # The 0.7 runs (exp-34/36/37, and exp-31 hard) proved the stall-fix and are the larger-n
        # evidence; they are the recommended-config PREDECESSOR and now live in the narrative,
        # not the featured numbers. 0.35 runs (exp-29/30/32/33) are the original stall-bound
        # baseline. See docs/past-experiments.md exp-38/39.
        "name": "Qwen3-Coder-Next 80B (local, $0, ctx 0.9)",
        "short": "Qwen 80B local",
        "where": (
            "( experiment LIKE '%experiment-38%' OR experiment LIKE '%experiment-39%' )"
        ),
        "kind": "local",
        # ONE BAR FOR EVERYONE. This was 0.50 for local stacks on the reasoning
        # that a $0 stack is worth a lower bar if you are watching it. That
        # contradicted this document's own definition of the metric — "the
        # probability a single UNATTENDED run comes out completely correct", where
        # "a single sub-1.0 run is a fail" — and it let a coin flip outrank a
        # perfect stack purely on price: python-on-hard-task recommended the local
        # 35B at 0.50. Being free is already represented, in the cost column.
        # Holding local to 1.00 did not remove local from the recommendations; it
        # switched routine python/go from the 35B (0.85/0.87) to the 80B (1.00),
        # still at $0. The double standard was hiding the better local stack.
        "pass_bar": 1.00,
        "cost_override": 0.0,
        # Headline aggregate scoped to the 80B's RECOMMENDED languages (python/go/ts,
        # each 3/3=1.00 at ctx 0.9). exp-38 also ran rust (1/3) and 5 niche languages
        # (0/3) that go to cloud; averaging them in would drag the decision-table number
        # to ~0.37 and wrongly rank the 80B below the 35B, which it beats on every shared
        # language. The per-language matrix stays unscoped and shows rust + the niche
        # 0.00s in full.
        "routine_scope": ["python", "go", "typescript"],
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
    "mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8":
        "gpt-oss-20b (exp-47): evaluated, deliberately NOT featured — go 3/3 at 95s "
        "(80B parity, 3.6x faster) but python 1/3, so it is the 'fast Go option', "
        "not a recommendable default. Revisit if a follow-up firms up Go at n>=5.",
}


def q(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def stack_where(s):
    """SQL predicate selecting a stack's rows: explicit `where`, else `model IN (...)`."""
    if "where" in s:
        return s["where"]
    lits = ",".join("'" + m.replace("'", "''") + "'" for m in s["models"])
    return f"model IN ({lits})"


def metrics(conn, where, task, language=None, languages=None):
    """n, pass-proportion, avg cost, avg seconds for a selection on one task.

    `language` restricts to a single language (used by the per-language matrix).
    `languages` (a list) restricts to a set — used by the leading-stacks table to
    scope a local stack's HEADLINE aggregate to the languages it is recommended for
    (`routine_scope`), so a full-suite experiment that also probed languages the
    stack can't do (and which you'd send to cloud) doesn't drag the decision-table
    number below a stack that was simply never tried on those hard languages. The
    per-language matrix stays UNSCOPED, so the raw per-language truth (incl. the
    niche 0.00s) is always visible for scrutiny.
    """
    clause = f"({where}) AND task = ? AND {BASE_FILTER}"
    params = [task]
    if language is not None:
        clause += " AND language = ?"
        params.append(language)
    if languages:
        placeholders = ",".join("?" for _ in languages)
        clause += f" AND language IN ({placeholders})"
        params.extend(languages)
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
        r = metrics(conn, stack_where(s), ROUTINE_TASK, languages=s.get("routine_scope"))
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
def per_language_routing(conn, task=ROUTINE_TASK):
    """Per language, the CHEAPEST featured stack that clears its pass-bar on
    ``task`` — the measured routing decision. Returns a dict keyed by language:
    ``{lang: {"stack", "models", "cost", "pass", "n"} | None}`` (None = no
    qualifying stack in the db). This is the machine-readable form of the
    "cheapest qualifying" table — the data a router (metaharness) consumes to pick
    the cheapest model that maintains a high success rate for each language/task.
    """
    routing: dict[str, dict | None] = {}
    for lang in routine_languages(conn):
        candidates = []
        for s in FEATURED_STACKS:
            # A stack is (model × THINKING LEVEL), not a model alone. exp-49
            # measured `low` at ~25% less cost than the CLI default for an
            # identical 1.00 on the routine task, so collapsing over effort
            # would recommend a needlessly expensive operating point. Each
            # effort level a stack has actually been measured at competes
            # separately; `default` covers every run made before the factor
            # existed, which is most of the corpus.
            for eff in efforts_for(conn, s, task, lang):
                where = stack_where(s)
                if eff is not None:
                    where = f"({where}) AND effort = '{eff}'"
                m = metrics(conn, where, task, language=lang)
                if m["n"] and m["pass"] >= s["pass_bar"]:
                    cost = s.get(
                        "cost_override", m["cost"] if m["cost"] is not None else 1e9
                    )
                    candidates.append((cost, s, m, eff))
        if not candidates:
            routing[lang] = None
            continue
        # Cheapest qualifying; ties broken toward the better-replicated cell so a
        # lucky n=1 outlier doesn't beat a well-measured alternative on noise.
        candidates.sort(key=lambda c: (c[0], -c[2]["n"]))

        def record(entry):
            cost, s, m, eff = entry
            return {
                "stack": s["name"],
                "models": list(s.get("models", [])),
                "effort": eff or "default",
                "cost": 0.0 if s.get("cost_override") == 0.0 else m["cost"],
                "pass": m["pass"],
                "n": m["n"],
            }

        # LOCAL AND CLOUD ARE REPORTED SEPARATELY, not merged into one winner.
        #
        # A local stack costs $0 marginal, so "cheapest overall" is always local
        # wherever local qualifies — which hides the only number a reader without
        # that hardware can act on, and makes `effort` read "default" simply
        # because the local stack was never swept. The two are also not really
        # comparable: local is MACHINE-SPECIFIC (this is a 64 GB M5; a different
        # box gets different answers), while a cloud stack is reproducible by
        # anyone with an API key.
        #
        # So each cell reports the best of each kind. `local` may be null (no
        # local stack clears the bar) and so may `cloud`; null means "nothing
        # measured qualifies", never "untested".
        entry = {}
        for kind in ("cloud", "local"):
            pick = next((c for c in candidates if c[1].get("kind") == kind), None)
            entry[kind] = record(pick) if pick else None
        routing[lang] = entry
    return routing


def _best(rec, kind="cloud"):
    """The chosen record of one kind from a routing cell, or None.

    Tolerates the older flat shape (a single winner per cell) so callers written
    against it keep working.
    """
    if not rec:
        return None
    if kind in rec or "cloud" in rec:
        return rec.get(kind)
    return rec  # legacy flat record


def efforts_for(conn, stack, task, language):
    """Thinking levels this stack has actually been MEASURED at for this cell.

    Returns ``[None]`` (meaning "don't filter on effort") when the cell has only
    ever run at one level — which is true for almost everything, since `effort`
    only became a factor in exp-49. Reporting a level we never varied would imply
    a comparison that was never made.
    """
    try:
        rows = q(
            conn,
            f"SELECT DISTINCT COALESCE(effort,'default') FROM runs "
            f"WHERE ({stack_where(stack)}) AND task = ? AND language = ? AND {BASE_FILTER}",
            (task, language),
        )
    except sqlite3.OperationalError:
        # No `effort` column (an older master.db, or a test fixture that predates
        # the factor) — behave exactly as before it existed.
        return [None]
    # Index rather than key: callers may or may not have set a row_factory.
    levels = sorted({r[0] for r in rows if r[0]})
    return levels if len(levels) > 1 else [None]


def model_board(conn):
    """Per-STACK summary on both tasks — the board at the top of model-blog.

    Generated from the same FEATURED_STACKS curation as everything else, so the
    published table and `optimal.json`'s `models` block are the same numbers by
    construction rather than by transcription. Before this existed the board was
    maintained by hand and drifted: it once showed Opus 4.8 at 1.00 on the hard
    task (a three-language subset) while the prose two screens down said 0.59.
    """
    rows = []
    for s in FEATURED_STACKS:
        # Scope a local stack's ROUTINE number to the languages it is actually
        # recommended for, exactly as the leading-stacks table does — otherwise
        # the same stack reports two different figures in the same repo. Without
        # this the 80B reads 0.37, because the average is dragged down by the
        # niche languages it cannot do and which you would send to cloud anyway.
        # The per-language matrix stays unscoped and shows those 0.00s in full.
        easy = metrics(conn, stack_where(s), ROUTINE_TASK,
                       languages=s.get("routine_scope"))
        hard = metrics(conn, stack_where(s), HARD_TASK)
        rows.append({
            "stack": s["name"],
            "short": s["short"],
            "kind": s["kind"],
            "routine": None if not easy["n"] else {
                "pass": round(easy["pass"], 2), "n": easy["n"],
                "cost": 0.0 if s.get("cost_override") == 0.0 else round(easy["cost"] or 0, 2),
            },
            "hard": None if not hard["n"] else {
                "pass": round(hard["pass"], 2), "n": hard["n"],
                "cost": 0.0 if s.get("cost_override") == 0.0 else round(hard["cost"] or 0, 2),
            },
        })
    return rows


def model_board_table(conn):
    lines = ["| Stack | Serving | Easy: pass | Easy: $ | Hard: pass | Hard: $ |",
             "|---|---|---:|---:|---:|---:|"]
    for r in model_board(conn):
        serving = "**local · $0**" if r["kind"] == "local" else "cloud"
        def cells(d):
            if not d:
                return ("*not run*", "—")
            v = f"{d['pass']:.2f} ({d['n']})"
            v = f"**{v}**" if d["pass"] >= 1.0 else v
            return (v, "$0" if d["cost"] == 0.0 else f"${d['cost']:.2f}")
        ep, ec = cells(r["routine"])
        hp, hc = cells(r["hard"])
        name = f"**{r['stack']}**" if r["kind"] == "local" else r["stack"]
        lines.append(f"| {name} | {serving} | {ep} | {ec} | {hp} | {hc} |")
    return "\n".join(lines)


def per_language_routing_table(conn):
    """Best CLOUD (model @ effort) and best LOCAL, per language, both task sizes.

    Cloud first because it is reproducible by anyone; local is reported beside it
    but is MACHINE-SPECIFIC (these numbers are a 64 GB M5) and $0 marginal, so
    merging the two into one "winner" would let $0 hide the only figure most
    readers can act on.
    """
    routine = per_language_routing(conn, ROUTINE_TASK)
    hard = per_language_routing(conn, HARD_TASK)
    langs = sorted(set(routine) | set(hard))
    lines = [
        "| Language | Routine → cloud | pass | $ | Routine → local | Hard → cloud | pass | $ |",
        "|---|---|---:|---:|---|---|---:|---:|",
    ]

    def short(r):
        if not r:
            return "—"
        s = r["stack"].replace("Claude ", "").replace(" (codex)", "")
        s = s.replace(" (local, $0)", "").replace(" (local, $0, ctx 0.9)", "")
        return f"{s} @ `{r['effort']}` <sub>n={r['n']}</sub>"

    def money(r):
        if not r:
            return "—"
        return "$0" if r["cost"] == 0.0 else f"${r['cost']:.2f}"

    def rate(r):
        if not r:
            return "—"
        v = f"{r['pass']:.2f}"
        return f"**{v}**" if r["pass"] < 1.0 else v

    for lang in langs:
        rc, rl = _best(routine.get(lang), "cloud"), _best(routine.get(lang), "local")
        hc = _best(hard.get(lang), "cloud")
        lines.append(
            f"| **{lang}** | {short(rc)} | {rate(rc)} | {money(rc)} | {short(rl)} "
            f"| {short(hc)} | {rate(hc)} | {money(hc)} |"
        )
    return "\n".join(lines)


def per_language_table(conn):
    routing = per_language_routing(conn)
    lines = [
        "| Language | Routine → cheapest qualifying stack | Reliability | n |",
        "|---|---|---:|---:|",
    ]
    for lang, rec in routing.items():
        c_, l_ = _best(rec, "cloud"), _best(rec, "local")
        # cheapest of whichever kinds qualify
        r = min((x for x in (c_, l_) if x), key=lambda x: x["cost"], default=None)
        if r is None:
            lines.append(f"| **{lang}** | *no qualifying stack in db* | — | — |")
            continue
        cost_str = "$0" if r["cost"] == 0.0 else f"${r['cost']:.2f}"
        lines.append(
            f"| **{lang}** | {r['stack']} ({cost_str}) | {r['pass']:.2f} | {r['n']} |"
        )
    return "\n".join(lines)


def routing_config(conn):
    """The full retort→metaharness routing table: per (task, language) the
    cheapest measured stack that maintains high success. A machine-readable feed
    so metaharness routes from Retort's OPTIMAL-BLOG results (measured) instead of
    hand-heuristics — and can be contributed back upstream. Shape:
    ``{"source": "retort optimal-blog", "objective": "min cost @ pass-bar",
       "routes": {task: {lang: {stack, models, cost, pass, n}}}}``.
    """
    routes = {}
    for task in (ROUTINE_TASK, HARD_TASK):
        routes[task] = per_language_routing(conn, task=task)
    return {
        "source": "retort report optimal (master.db)",
        "objective": "cheapest featured stack per language/task that clears its pass-bar",
        "notes": {
            "effort": (
                "The thinking level of the CHOSEN cell. 'default' means that stack "
                "ran with no effort flag — it is the level those runs used, not a "
                "recommendation, and for most stacks it is the only level ever "
                "measured. Where a stack HAS been swept (GPT-5.6 Terra, Opus 5) "
                "each level competes separately and the cheapest qualifying one "
                "is picked."
            ),
            "cheapest_cloud/cheapest_local": (
                "The best option of each kind, because 'cheapest overall' alone is "
                "not actionable: a local stack at $0 wins every cell it qualifies "
                "for, hiding the best answer for anyone who cannot run models "
                "locally. Either may be null if nothing of that kind clears the bar."
            ),
            "null": "No measured stack clears the bar for that cell. NOT 'untested'.",
            "n": "Replicates behind pass and cost. Several cells are n=1; cost is a "
                 "point estimate with no error bar and the selection does not weight by n.",
            "cost": "List price per token for every metered stack (what Claude's CLI "
                    "reports and a Max plan does not bill; computed for codex, which "
                    "reports nothing). Local stacks are $0 marginal by override.",
        },
        "models": model_board(conn),
        "routes": routes,
    }


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
        "per-language-routing": per_language_routing_table(conn),
        "model-board": model_board_table(conn),
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
