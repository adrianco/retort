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
from retort.scoring.scorers import runtime as rt

#: Tool-name fragments that plausibly answer "the 2019 Série A table", best first.
_STANDINGS_HINTS = ("standing", "table", "league_table", "season_table",
                    "classification", "season", "league")

#: The season the golden answers describe.
GOLDEN_SEASON = 2019

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


def _atletico_rows(text: str) -> int:
    """How many DISTINCT rows name an Atlético/Athletico club.

    2019 Série A had two: Athletico Paranaense (5th) and Atlético Mineiro (13th).
    Implementations render them as "Athletico Paranaense" / "Athletico" /
    "Atletico" and "Atlético Mineiro" / "Atlético-MG" / "Atletico" — and in at
    least one case BOTH appear as an identical bare "Atletico". Counting rows is
    therefore the only check the data actually supports; asking for each by name
    reported two correct implementations as missing a club.
    """
    return sum(1 for line in text.splitlines()
               if re.search(r"(?<![a-z])ath?letico", _fold(line)))


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

    def as_dict(self) -> dict:
        return {"ok": self.ok, "score": self.score, "note": self.note,
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
    for line in text.splitlines():
        if want in line.lower():
            nums = [int(n) for n in re.findall(r"-?\d+", line)]
            if len(nums) >= 3:            # a rank/­name line alone is not a row
                return nums
    return []


def _call(proc, name: str, args: dict, rid: int, budget: float) -> dict | None:
    try:
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                                     "params": {"name": name, "arguments": args}}) + "\n")
        proc.stdin.flush()
    except (BrokenPipeError, OSError):
        return None
    deadline = time.perf_counter() + budget
    while time.perf_counter() < deadline:
        line = rt._readline_timeout(proc, deadline)
        if not line:
            return None
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            msg = json.loads(s)
        except ValueError:
            continue
        if msg.get("id") == rid:
            return msg
    return None


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
    season_key = next((k for k in props if "season" in k.lower() or "year" in k.lower()), None)
    comp_key = next((k for k in props if "competition" in k.lower() or "league" in k.lower()
                     or "tournament" in k.lower()), None)
    seasons: list = [GOLDEN_SEASON]
    if season_key and (props.get(season_key, {}) or {}).get("type") == "string":
        seasons = [str(GOLDEN_SEASON)]
    out: list[dict] = []
    comps = ["serie-a", "Serie A", "Série A", "Campeonato Brasileiro Série A", "Brasileirao"]
    for s in seasons:
        if comp_key:
            for c in comps:
                out.append({season_key: s, comp_key: c} if season_key else {comp_key: c})
        if season_key:
            out.append({season_key: s})
    return out or [{}]


def measure(run_dir: Path, language: str) -> FactualResult:
    """Start the server and check its answers against known 2019 results."""
    res = FactualResult()
    cmd, why = rt._build_then_entry(run_dir, language)
    if cmd is None:
        res.note = why or "no runnable entrypoint"
        return res

    errf = rt._stderr_file()
    try:
        proc = subprocess.Popen(cmd, cwd=run_dir.resolve(), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=errf, text=True, bufsize=1)
    except (FileNotFoundError, OSError) as exc:
        res.note = f"could not start: {exc}"
        errf.close()
        return res

    try:
        captured: dict = {}
        listed = rt._mcp_handshake(proc, rt.ITER_TIMEOUT_S, captured)
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
        rid = 800
        for tool in sorted(tools, key=rank)[:4]:
            if rank(tool) == len(_STANDINGS_HINTS):
                break                                  # nothing standings-shaped left
            for args in _standings_args(tool.get("inputSchema", {}) or {})[:6]:
                rid += 1
                msg = _call(proc, tool.get("name", ""), args, rid, rt.QUERY_TIMEOUT_S)
                if not msg or "error" in msg:
                    continue
                if (msg.get("result") or {}).get("isError"):
                    continue
                text = _text_of(msg)
                if "flamengo" in text.lower():
                    table_text = text
                    break
            if table_text:
                break

        if not table_text:
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
        nums = _row_numbers(table_text, "Flamengo")
        record_ok = any(nums[i:i + 3] == [28, 6, 4] for i in range(len(nums)))
        res.assertions.append(Assertion(
            name="2019 Série A: Flamengo's record",
            expected="28W-6D-4L (= 38 played, 90 points)",
            actual=("28W-6D-4L" if record_ok else
                    (f"row figures {nums}" if nums else "no Flamengo row found")),
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
            proc.kill()
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
