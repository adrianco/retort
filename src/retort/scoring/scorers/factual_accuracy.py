"""Are the produced program's ANSWERS right — not just present?

`requirement_coverage` asks whether a capability EXISTS ("a tool filters matches
by team name"), never whether its numbers are correct, and the agents' own tests
assert accounting identities (`matches == wins+draws+losses`) that stay true when
every match is counted twice. So a brazil-bench run can score 12/12 while
double-counting the entire corpus: the five Kaggle match files overlap on
purpose (BR-Football 2014-2023, Brasileirao_Matches 2012-2022, novo_campeonato
2003-2019), and 23,954 rows is exactly their sum — i.e. no deduplication at all.
Measured across the archive, 4 of the 22 runs that self-report their load are in
that state, and every one of them passed.

This scorer asks the finished server questions whose answers are externally
verifiable facts about Brazilian football, not artefacts of the corpus:

  * 2019 Série A is a 20-team double round-robin → EVERY club played exactly 38.
    A run that counts each fixture twice reports ~76.
  * Flamengo won it on 90 points.

Both are stated in the task's own worked example, so this tests conformance to
the spec as written rather than adding a new requirement.

WHY IT GATES, AND WHY A DEAD SERVER FAILS.
`REQUIREMENTS.json` stays pinned — this is a NEW response column, so
`requirement_coverage` and every historical brazil number keep their meaning.
But a run that answers wrongly is not a pass, so this participates in the gate,
and a server that cannot be STARTED fails it: an artifact that does not run is a
broken deliverable, and the harness already has a separate mechanism for
harness-caused failures (it aborts the experiment rather than recording them).

That is deliberately the OPPOSITE of `runtime`, which returns None when it
cannot measure. Runtime is a measurement — "could not measure" is not "slow", and
recording 0 there would enter a per-language mean as infinitely slow. This is a
gate — "did not answer correctly" and "did not answer at all" are both failures
of the artifact. Do not harmonise them.

Every failure is written to `_factual.json` with the expected and actual value so
the self-repair second chance gets a specific, actionable defect rather than
"you failed".
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring import probe_status
from retort.scoring.scorers import runtime as rt

#: Tool-name fragments that plausibly answer "the 2019 Série A table", best first.
_STANDINGS_HINTS = ("standing", "table", "league_table", "season_table",
                    "classification", "season", "league")

#: The season the golden answers describe.
GOLDEN_SEASON = 2019

#: Most rows a 2019 Série A answer can plausibly have. The league has 20 clubs;
#: the slack absorbs a header or summary row. Beyond this the response is a
#: different question's answer (all competitions that season), not a wrong one.
_MAX_PLAUSIBLE_ROWS = 26

#: The 20 clubs of the 2019 Brasileirão Série A, each with a DISTINCTIVE token to
#: match on. Tokens rather than full names because the corpus and the
#: implementations disagree about accents and the state suffix
#: (`São Paulo` / `Sao Paulo` / `Sao Paulo-SP`), and because "Atlético Mineiro"
#: and "Athletico Paranaense" both normalise to "atletico" — so those two are
#: matched on `mineiro` and `paranaense` instead.
#: The 18 clubs whose names identify them unambiguously. The two Atléticos are
#: NOT here — see _atletico_rows: some implementations render both as a bare
#: "Atletico", so the name alone cannot tell Paranaense from Mineiro and asking
#: it to wrongly failed correct work.
#:
#: Each club maps to ALTERNATIVE tokens; any one of them counts as present.
#: The two Atléticos are why: implementations render them as "Athletico
#: Paranaense" / "Athletico" / "Atlético-PR", and "Atlético Mineiro" /
#: "Atlético-MG". Accent folding keeps the pair distinguishable — Paranaense is
#: spelled with the h ("athletico"), Mineiro without ("atletico") — but a single
#: token per club wrongly reported two CORRECT implementations as missing both.
SERIE_A_2019: list[tuple[str, tuple[str, ...]]] = [
    ("Flamengo", ("flamengo",)), ("Santos", ("santos",)),
    ("Palmeiras", ("palmeiras",)), ("Grêmio", ("gremio",)),
    ("São Paulo", ("sao paulo",)), ("Internacional", ("internacional",)),
    ("Corinthians", ("corinthians",)), ("Fortaleza", ("fortaleza",)),
    ("Goiás", ("goias",)), ("Bahia", ("bahia",)), ("Vasco da Gama", ("vasco",)),
    ("Fluminense", ("fluminense",)), ("Botafogo", ("botafogo",)),
    ("Ceará", ("ceara",)), ("Cruzeiro", ("cruzeiro",)), ("CSA", ("csa",)),
    ("Chapecoense", ("chapecoense",)), ("Avaí", ("avai",)),
]


def _fold(text: str) -> str:
    """Lowercase and strip accents, so `Avaí` and `Avai` compare equal."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower())
                   if unicodedata.category(c) != "Mn")


def _rows_of(text: str) -> list[str]:
    """The table as one string PER CLUB, whatever shape the server returned.

    Implementations answer with a text table, a markdown table, or a single line
    of JSON. Line-based parsing silently collapses the JSON case to ONE row, so
    every club check saw a single row and reported "19 of 20 (1 Atletico row)"
    for tables that were completely correct — Flamengo 38 played, 90 points, all
    20 clubs present. Parse the structure when there is one.
    """
    stripped = text.strip()
    # JSON may be EMBEDDED, not the whole payload: one server answers
    # "Competition analysis covers 380 matches.\n{ ...pretty-printed... }".
    # That parses neither as JSON nor line-wise (the team name sits on its own
    # line with no figures), so a correct table read as "no Flamengo row found".
    if not (stripped.startswith("[") or stripped.startswith("{")):
        first = min((i for i in (stripped.find("{"), stripped.find("[")) if i >= 0),
                    default=-1)
        if first >= 0:
            stripped = stripped[first:]
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except ValueError:
            data = None
        if isinstance(data, dict):
            for key in ("standings", "table", "rows", "teams", "result", "data"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if isinstance(data, list) and data:
            out = []
            for item in data:
                out.append(json.dumps(item) if isinstance(item, (dict, list)) else str(item))
            return out
    return text.splitlines()


#: Field names a structured row may use for each figure, in preference order.
_FIELD_ALIASES = {
    "played": ("played", "matches", "matches_played", "games", "p", "mp"),
    "wins": ("wins", "won", "w"),
    "draws": ("draws", "drawn", "ties", "d"),
    "losses": ("losses", "lost", "defeats", "l"),
    "points": ("points", "pts"),
}


def _record_from_fields(row: str) -> dict | None:
    """W/D/L/played/points read BY NAME from a structured row, if it is one.

    Positional parsing cannot work here. One server returns
    `{"draws": 6, "goal_difference": 49, ..., "points": 90, "wins": 28}` — every
    figure correct, but JSON key order is alphabetical, so a check for the
    consecutive triple [28, 6, 4] fails on a perfect answer. Read the fields.

    NESTED rows count too. The rust implementation in exp-60 answers
    `{"team": "Flamengo-RJ", "points": 90, "record": {"matches": 38, "wins": 28,
    "draws": 6, "losses": 4, ...}}` — the correct table, with the record under a
    sub-object. Reading only top-level keys found `points` and nothing else, so
    the gate reported "expected 28W-6D-4L, got fields {'points': 90}" and FAILED
    a run whose answer was right. That is the project's oldest bug wearing a new
    hat: the scorer was measuring JSON SHAPE and reporting it as a fact error.
    Flattening one level is enough for every shape seen so far, and a nested key
    never overrides a top-level one of the same name.
    """
    row = row.strip()
    if not row.startswith("{"):
        return None
    try:
        obj = json.loads(row)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    lowered = {str(k).lower(): v for k, v in obj.items()}
    for value in list(obj.values()):
        if isinstance(value, dict):
            for k, v in value.items():
                lowered.setdefault(str(k).lower(), v)
    out: dict = {}
    for want, aliases in _FIELD_ALIASES.items():
        for a in aliases:
            if isinstance(lowered.get(a), (int, float)):
                out[want] = int(lowered[a])
                break
    return out or None


def _atletico_rows(text: str) -> int:
    """How many DISTINCT rows name an Atlético/Athletico club.

    2019 Série A had two: Athletico Paranaense (5th) and Atlético Mineiro (13th).
    Implementations render them as "Athletico Paranaense" / "Athletico" /
    "Atletico" and "Atlético Mineiro" / "Atlético-MG" / "Atletico" — and in at
    least one case BOTH appear as an identical bare "Atletico". Counting rows is
    therefore the only check the data actually supports; asking for each by name
    reported two correct implementations as missing a club.
    """
    return sum(1 for row in _rows_of(text)
               if re.search(r"(?<![a-z])ath?letico", _fold(row)))


def _names_present(text: str, tokens: tuple[str, ...]) -> bool:
    """True if ANY spelling of the club appears in an accent-folded haystack.

    Word boundaries matter: `csa` would otherwise match inside unrelated words.
    A trailing state suffix is allowed, so `atletico` matches `atletico-mg`.
    """
    folded = _fold(text)
    return any(re.search(rf"(?<![a-z]){re.escape(tok)}(?![a-z])", folded)
               for tok in tokens)


@dataclass
class Assertion:
    """One externally-verifiable fact, and what the server actually said."""

    name: str
    expected: str
    actual: str = ""
    passed: bool = False
    #: Plain-English repair guidance shown to the agent when this fails.
    hint: str = ""

    def as_dict(self) -> dict:
        return {"name": self.name, "expected": self.expected, "actual": self.actual,
                "passed": self.passed, "hint": self.hint}


@dataclass
class FactualResult:
    ok: bool = False
    score: float = 0.0
    note: str = ""
    assertions: list[Assertion] = field(default_factory=list)
    #: The server's OWN answer, verbatim (truncated). Without it a verdict is
    #: unauditable: exp-60's rust cell failed with "expected 28W-6D-4L, got
    #: fields {'points': 90}" and nothing in the archive could say whether the
    #: server was wrong or the parser was — it was the parser. A failing program
    #: and a broken measurement must not look identical in the output.
    raw: str = ""
    tool: str = ""
    #: What the probe actually installed to run this — see runtime._venv_freeze.
    #: A run here fails with `AttributeError: 'Server' object has no attribute
    #: 'list_tools'`, and whether that is the model's defect or an artifact of
    #: resolving its dependencies years later cannot be told from the traceback.
    deps: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "score": self.score, "note": self.note,
                "tool": self.tool, "raw": self.raw, "deps": self.deps,
                "assertions": [a.as_dict() for a in self.assertions]}

    def feedback_lines(self) -> list[str]:
        """The lines that go into FEEDBACK.md for the self-repair attempt."""
        failed = [a for a in self.assertions if not a.passed]
        if not failed and self.ok:
            return []
        out = ["", "## Factual accuracy — your answers were checked against known results"]
        if not self.assertions:
            out.append(f"- The server could not be started or did not answer: {self.note}")
            out.append("- A correct implementation must start from its documented entrypoint "
                       "and serve MCP over stdio. Fix that first — nothing else can be checked.")
            return out
        for a in failed:
            out.append(f"- **{a.name}** — expected {a.expected}, got {a.actual or 'no answer'}.")
            if a.hint:
                out.append(f"  {a.hint}")
        return out


def _row_numbers(text: str, team: str) -> list[int]:
    """Integers on the line describing `team`, in order.

    Deliberately format-agnostic: implementations return a text table, markdown,
    or JSON, and the only thing they share is that the club's figures sit near
    its name. Accents vary too (`São Paulo` vs `Sao Paulo`), so matching is
    done on a normalised, case-folded substring.
    """
    want = team.lower()
    for row in _rows_of(text):
        if want in row.lower():
            nums = [int(n) for n in re.findall(r"-?\d+", row)]
            if len(nums) >= 3:            # a rank/name fragment alone is not a row
                return nums
    return []


def _call(proc, name: str, args: dict, rid: int, budget: float) -> dict | None:
    """One tools/call, via the SHARED protocol helpers in `runtime`.

    This was a fourth hand-rolled copy of send-then-await-by-id. The copies had
    already drifted — only one scraped the start-up banner — so `rows_loaded`
    was populated on some paths and silently NULL on others.
    """
    if not rt.mcp_send(proc, {"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                              "params": {"name": name, "arguments": args}}):
        return None
    return rt.mcp_await_id(proc, rid, budget)


def _text_of(msg: dict) -> str:
    result = msg.get("result") or {}
    parts = []
    for c in result.get("content", []) or []:
        if isinstance(c, dict) and c.get("text"):
            parts.append(c["text"])
    if not parts:
        parts.append(json.dumps(result))
    return "\n".join(parts)


def _standings_args(schema: dict) -> list[dict]:
    """Argument sets to try for a standings call, most specific first.

    Built from the tool's OWN schema — competition naming is not pinned by the
    task, so implementations use `serie-a`, `Serie A`, `Brasileirão Série A`,
    or no competition parameter at all.
    """
    props = schema.get("properties", {}) or {}
    # Consider REQUIRED names too, not just declared properties. One server ships
    # `{"required": ["season"], "type": "object"}` with no properties block at
    # all; building args from properties alone sent `{}`, so it was never asked
    # for 2019 and correctly answered with all-time standings (Flamengo: 1085
    # played). The probe then reported a working implementation as wrong.
    keys = list(props) + [k for k in (schema.get("required") or []) if k not in props]
    season_key = next((k for k in keys if "season" in k.lower() or "year" in k.lower()), None)
    comp_key = next((k for k in keys if "competition" in k.lower() or "league" in k.lower()
                     or "tournament" in k.lower()), None)
    seasons: list = [GOLDEN_SEASON]
    if season_key and (props.get(season_key, {}) or {}).get("type") == "string":
        seasons = [str(GOLDEN_SEASON)]
    out: list[dict] = []
    # "Brasileirão" — WITH the tilde — is the string the corpus itself uses, and
    # its absence here cost a correct run a pass: every filtered call missed, the
    # probe fell back to season-only, and the server correctly answered with ALL
    # 2019 competitions. That table has Série A and Série B in it (Bragantino,
    # five Atléticos), and the gate judged the model on it. Asking the wrong
    # question and grading the right answer is the harness's error, not the
    # model's.
    comps = ["serie-a", "Serie A", "Série A", "Brasileirão", "Brasileirao",
             "Brasileirão Série A", "Campeonato Brasileiro Série A",
             "Campeonato Brasileiro"]
    for s in seasons:
        if comp_key:
            for c in comps:
                out.append({season_key: s, comp_key: c} if season_key else {comp_key: c})
        if season_key:
            out.append({season_key: s})
    return out or [{}]


#: Total wall clock for one factual check. Same reasoning as runtime's
#: PROBE_BUDGET_S: four tool attempts at the query timeout plus a handshake is
#: 8.5 minutes per cell on a server that will not answer, and inline that turns
#: scoring into the experiment.
FACTUAL_BUDGET_S = 120.0


def measure(run_dir: Path, language: str,
            budget_s: float = FACTUAL_BUDGET_S) -> FactualResult:
    """Start the server and check its answers against known 2019 results.

    Announced to the live monitor for its whole duration — this phase launches
    the model's program, not an agent, so it is otherwise invisible.
    """
    with probe_status.announcing(f"checking answers ({language})", language):
        return _measure(run_dir, language, budget_s)


def _measure(run_dir: Path, language: str, budget_s: float) -> FactualResult:
    budget = rt._Budget(budget_s)
    res = FactualResult()
    cmd, why = rt._build_then_entry(run_dir, language, res.deps)
    if cmd is None:
        res.note = why or "no runnable entrypoint"
        return res

    errf = rt._stderr_file()
    try:
        proc = rt._spawn(cmd, run_dir.resolve(), errf)
    except (FileNotFoundError, OSError) as exc:
        res.note = f"could not start: {exc}"
        errf.close()
        return res

    try:
        captured: dict = {}
        listed = rt._mcp_handshake(proc, budget.slice(rt.ITER_TIMEOUT_S), captured)
        if listed is None:
            res.note = rt._stderr_tail(errf) or "did not complete the MCP handshake"
            return res
        tools = (listed.get("result") or {}).get("tools") or []

        def rank(t: dict) -> int:
            n = t.get("name", "").lower()
            for i, h in enumerate(_STANDINGS_HINTS):
                if h in n:
                    return i
            return len(_STANDINGS_HINTS)

        table_text = ""
        #: A Flamengo-naming answer that was too large to be the 2019 Série A
        #: table. Kept only so the note can say what happened.
        oversized = ""
        rid = 800
        for tool in sorted(tools, key=rank)[:4]:
            if rank(tool) == len(_STANDINGS_HINTS):
                break                                  # nothing standings-shaped left
            for args in _standings_args(tool.get("inputSchema", {}) or {})[:6]:
                if budget.spent():
                    break
                rid += 1
                msg = _call(proc, tool.get("name", ""), args, rid,
                            budget.slice(rt.QUERY_TIMEOUT_S))
                if not msg or "error" in msg:
                    continue
                if (msg.get("result") or {}).get("isError"):
                    continue
                text = _text_of(msg)
                if "flamengo" not in text.lower():
                    continue
                # A 2019 Série A table has 20 rows. A much bigger one is not the
                # answer to the question asked — it is every competition that
                # season merged — so keep looking rather than grade it. Judging
                # an answer to a question you did not ask is how a correct
                # implementation gets failed.
                if len(_rows_of(text)) > _MAX_PLAUSIBLE_ROWS:
                    oversized = oversized or text
                    continue
                if True:
                    table_text = text
                    # Keep the answer itself, so a verdict can be checked
                    # against what the server actually said rather than trusted.
                    res.raw = text[:8000]
                    res.tool = tool.get("name", "")
                    break
            if table_text:
                break

        if not table_text:
            if budget.spent():
                res.note = "probe budget exhausted before any tool answered"
                return res
            if oversized:
                res.note = (
                    f"no tool returned a 20-row 2019 Série A table; the closest "
                    f"had {len(_rows_of(oversized))} rows, i.e. every competition "
                    "that season merged — the probe could not ask the question "
                    "narrowly enough to grade this server")
                res.raw = oversized[:8000]
                return res
            res.note = ("no tool returned a 2019 Série A table naming Flamengo "
                        f"(tried {min(len(tools), 4)} candidate tools)")
            return res

        # Flamengo's 2019 record is 28W-6D-4L. Assert THAT, not a "played"
        # column, because implementations format the row completely differently
        # and half of them print no played column at all:
        #
        #   "1. Flamengo - 90 pts (28W, 6D, 4L) GF 86 GA 37"   <- no P column
        #   "1 Flamengo   38  28  6  4  86  37 +49  90"        <- P column
        #
        # An earlier version looked for the literal 38 and, failing that, took
        # the first number in a plausible range — which picked up the POINTS
        # column and reported a CORRECT Rust implementation as answering "90
        # matches played". A gate that fails correct work is worse than no gate.
        # The W-D-L triple appears consecutively in every format observed, and it
        # determines both 38 played and 90 points, so it is the robust check.
        # Prefer FIELDS when the row is structured; fall back to the positional
        # triple for text tables.
        flam = next((r for r in _rows_of(table_text) if "flamengo" in r.lower()), "")
        fields = _record_from_fields(flam)
        nums = _row_numbers(table_text, "Flamengo")
        if fields and {"wins", "draws", "losses"} <= set(fields):
            record_ok = (fields["wins"], fields["draws"], fields["losses"]) == (28, 6, 4)
            if "played" in fields:
                record_ok = record_ok and fields["played"] == 38
            if "points" in fields:
                record_ok = record_ok and fields["points"] == 90
        else:
            record_ok = any(nums[i:i + 3] == [28, 6, 4] for i in range(len(nums)))
        res.assertions.append(Assertion(
            name="2019 Série A: Flamengo's record",
            expected="28W-6D-4L (= 38 played, 90 points)",
            actual=("28W-6D-4L" if record_ok else
                    (f"fields {fields}" if fields else
                     f"row figures {nums}" if nums else "no Flamengo row found")),
            passed=record_ok,
            hint=("2019 Série A is a 20-team double round-robin: every club plays "
                  "exactly 38 and Flamengo won on 90 points, as the task's own worked "
                  "example states. Roughly double those figures means the five match "
                  "files were concatenated without reconciling them — the same fixture "
                  "appears in two or three of them, and 23,954 rows is exactly their "
                  "sum. Deduplicate on (date, home, away) allowing a one-day "
                  "difference: sources disagree on local kick-off vs UTC date."),
        ))

        # The table must cover the whole division — checked by looking for the 20
        # clubs that actually played it, NOT by counting table-shaped lines. The
        # line-counting version reported 21 for two correct implementations,
        # because both append a summary ("Bottom four (relegation zone): 17.
        # Cruzeiro (36 pts), 18. CSA …") that looks exactly like a row.
        missing = sorted(c for c, toks in SERIE_A_2019 if not _names_present(table_text, toks))
        atleticos = _atletico_rows(table_text)
        n_found = (len(SERIE_A_2019) - len(missing)) + min(atleticos, 2)
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing[:5]))
        if atleticos != 2:
            detail.append(f"{atleticos} Atlético/Athletico row(s), expected 2")
        res.assertions.append(Assertion(
            name="2019 Série A: all 20 clubs present",
            expected="20 of 20",
            actual=f"{n_found} of 20" + (f" ({'; '.join(detail)})" if detail else ""),
            passed=not missing and atleticos == 2,
            hint=("The 2019 Brasileirão Série A had exactly these 20 clubs. Missing ones "
                  "usually mean the table was truncated for display — return the whole "
                  "table — or that a club's name variant (accents, the -SP/-MG state "
                  "suffix) was not normalised and so its matches were dropped."),
        ))

        # NOT asserted: that the server loaded fewer than 23,954 rows. Two runs
        # that load the full file sum answer 2019 correctly anyway — they filter
        # or reconcile inside the standings computation, and one reports
        # "1562 (889 counted once after de-duplication)" itself. Loading the sum
        # is a smell, not a defect; the answers are what count.

        res.score = sum(1 for a in res.assertions if a.passed) / len(res.assertions)
        res.ok = all(a.passed for a in res.assertions)
        if not res.ok:
            res.note = "; ".join(f"{a.name}: expected {a.expected}, got {a.actual}"
                                 for a in res.assertions if not a.passed)
        return res
    except (BrokenPipeError, OSError) as exc:
        res.note = f"server died during questioning: {exc}"
        return res
    finally:
        errf.close()
        try:
            rt._reap(proc)
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


class FactualAccuracyScorer:
    """Fraction of golden-answer assertions the produced server gets right.

    GATES. Unlike `runtime`, this never returns None: a server that will not
    start scores 0.0, because an artifact that does not run is a failed
    deliverable, not an unmeasurable one.
    """

    @property
    def name(self) -> str:
        return "factual_accuracy"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if artifacts.output_dir is None:
            return 0.0
        run_dir = Path(artifacts.output_dir)
        if rt.detect_task(run_dir) != "brazil-soccer-mcp":
            return 1.0            # N/A for other tasks, like bead_usage
        result = measure(run_dir, stack.language)
        try:
            (run_dir / "_factual.json").write_text(json.dumps(result.as_dict(), indent=1))
        except OSError:
            pass
        return result.score
