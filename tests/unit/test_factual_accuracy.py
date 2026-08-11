"""Golden-answer checks on the 2019 Série A table.

Every one of the 13 archived brazil implementations PASSES this scorer, which is
reassuring but proves only that it does not fail correct work. These tests prove
the other half — that it fails wrong work — using fabricated tables, since the
archive happens to contain no run whose 2019 standings are wrong.

Getting here took four false failures during development, each of which would
have failed a CORRECT implementation, and each caused by assuming a format the
implementations do not share:

  1. looking for the literal "38" and otherwise taking the first number in
     range — picked up the POINTS column on a Rust run that prints no played
     column at all ("1. Flamengo - 90 pts (28W, 6D, 4L)");
  2. counting table-shaped lines to get 20 clubs — counted a trailing summary
     ("Bottom four (relegation zone): 17. Cruzeiro (36 pts), …") as a 21st club;
  3. one token per club — "paranaense"/"mineiro" miss "Athletico" / "Atlético-MG";
  4. even with alternatives, one implementation renders BOTH Atléticos as a bare
     "Atletico", so they are only checkable as a pair.

The formats below are copied from real servers for exactly that reason.
"""
from __future__ import annotations

from retort.scoring.scorers import factual_accuracy as fa

# --- real output shapes, three different implementations ---------------------

COLUMNAR = """2019 Campeonato Brasileiro Série A — table calculated from match results

#   Team                       P   W   D   L   GF   GA   GD  Pts
1   Flamengo                  38  28   6   4   86   37  +49   90  Champion
2   Santos                    38  22   8   8   60   33  +27   74
3   Palmeiras                 38  21  11   6   61   32  +29   74
4   Grêmio                    38  19   8  11   64   39  +25   65
5   Athletico Paranaense      38  18  10  10   51   32  +19   64
6   São Paulo                 38  17  12   9   39   30   +9   63
7   Internacional             38  16   9  13   44   39   +5   57
8   Corinthians               38  14  14  10   42   34   +8   56
9   Fortaleza                 38  15   8  15   50   49   +1   53
10  Goiás                     38  15   7  16   46   64  -18   52
11  Bahia                     38  12  13  13   44   43   +1   49
12  Vasco da Gama             38  12  13  13   39   45   -6   49
13  Atlético Mineiro          38  13   9  16   45   49   -4   48
14  Fluminense                38  12  10  16   38   46   -8   46
15  Botafogo                  38  13   4  21   31   45  -14   43
16  Ceará                     38  10   9  19   36   41   -5   39
17  Cruzeiro                  38   7  15  16   27   46  -19   36
18  CSA                       38   8   8  22   24   58  -34   32
19  Chapecoense               38   7  11  20   31   52  -21   32
20  Avaí                      38   3  11  24   18   62  -44   20
Bottom four (relegation zone): 17. Cruzeiro (36 pts), 18. CSA (32 pts)
"""

#: No "played" column at all, and the Atléticos spelled differently.
NARRATIVE = """2019 Brasileirão Série A table (calculated from 380 matches in the dataset):
 1. Flamengo - 90 pts (28W, 6D, 4L) GF 86 GA 37 GD +49 - Champion
 2. Santos - 74 pts (22W, 8D, 8L) GF 60 GA 33 GD +27
 3. Palmeiras - 74 pts (21W, 11D, 6L) GF 61 GA 32 GD +29
 4. Grêmio - 65 pts (19W, 8D, 11L) GF 64 GA 39 GD +25
 5. Athletico - 64 pts (18W, 10D, 10L) GF 51 GA 32 GD +19
 6. São Paulo - 63 pts (17W, 12D, 9L) GF 39 GA 30 GD +9
 7. Internacional - 57 pts (16W, 9D, 13L) GF 44 GA 39 GD +5
 8. Corinthians - 56 pts (14W, 14D, 10L) GF 42 GA 34 GD +8
 9. Fortaleza - 53 pts (15W, 8D, 15L) GF 50 GA 49 GD +1
10. Goiás - 52 pts (15W, 7D, 16L) GF 46 GA 64 GD -18
11. Bahia - 49 pts (12W, 13D, 13L) GF 44 GA 43 GD +1
12. Vasco - 49 pts (12W, 13D, 13L) GF 39 GA 45 GD -6
13. Atlético-MG - 48 pts (13W, 9D, 16L) GF 45 GA 49 GD -4
14. Fluminense - 46 pts (12W, 10D, 16L) GF 38 GA 46 GD -8
15. Botafogo - 43 pts (13W, 4D, 21L) GF 31 GA 45 GD -14
16. Ceará - 39 pts (10W, 9D, 19L) GF 36 GA 41 GD -5
17. Cruzeiro - 36 pts (7W, 15D, 16L) GF 27 GA 46 GD -19
18. CSA - 32 pts (8W, 8D, 22L) GF 24 GA 58 GD -34
19. Chapecoense - 32 pts (7W, 11D, 20L) GF 31 GA 52 GD -21
20. Avaí - 20 pts (3W, 11D, 24L) GF 18 GA 62 GD -44
"""

#: BOTH Atléticos rendered identically — only checkable as a pair.
AMBIGUOUS_ATLETICOS = COLUMNAR.replace("Athletico Paranaense  ", "Atletico              ") \
                              .replace("Atlético Mineiro      ", "Atletico              ")

#: Every fixture counted twice: 38 -> 76 played, 90 -> 180 points.
DOUBLE_COUNTED = "\n".join(
    line.replace("38  28   6   4", "76  56  12   8").replace("  90  Champion", " 180  Champion")
    if "Flamengo" in line else line
    for line in COLUMNAR.splitlines()
)


def _assert_named(result, fragment):
    return next(a for a in result.assertions if fragment in a.name)


class _Res:
    """Minimal stand-in so the assertion builders can be exercised directly."""


def _evaluate(table: str) -> fa.FactualResult:
    """Run just the assertion logic over a table, without starting a server."""
    res = fa.FactualResult()
    nums = fa._row_numbers(table, "Flamengo")
    record_ok = any(nums[i:i + 3] == [28, 6, 4] for i in range(len(nums)))
    res.assertions.append(fa.Assertion(
        name="2019 Série A: Flamengo's record", expected="28W-6D-4L",
        actual="28W-6D-4L" if record_ok else f"row figures {nums}", passed=record_ok))
    missing = [c for c, toks in fa.SERIE_A_2019 if not fa._names_present(table, toks)]
    atl = fa._atletico_rows(table)
    res.assertions.append(fa.Assertion(
        name="2019 Série A: all 20 clubs present", expected="20 of 20",
        actual=f"{len(fa.SERIE_A_2019) - len(missing) + min(atl, 2)} of 20",
        passed=not missing and atl == 2))
    res.score = sum(1 for a in res.assertions if a.passed) / len(res.assertions)
    res.ok = all(a.passed for a in res.assertions)
    return res


# --- correct tables must PASS, in every observed format ----------------------

def test_columnar_table_passes():
    assert _evaluate(COLUMNAR).ok


def test_narrative_table_with_no_played_column_passes():
    """Regression: this shape once reported "90 matches played"."""
    assert _evaluate(NARRATIVE).ok


def test_both_atleticos_rendered_identically_still_passes():
    """Regression: neither club is identifiable by name here, only as a pair."""
    res = _evaluate(AMBIGUOUS_ATLETICOS)
    assert res.ok, _assert_named(res, "clubs").actual


def test_trailing_relegation_summary_is_not_a_21st_club():
    """Regression: the summary line was counted as an extra table row."""
    assert "relegation zone" in COLUMNAR
    assert _evaluate(COLUMNAR).ok


# --- wrong tables must FAIL --------------------------------------------------

def test_double_counted_table_fails():
    """The defect this scorer exists to catch: every fixture counted twice."""
    res = _evaluate(DOUBLE_COUNTED)
    assert not res.ok
    a = _assert_named(res, "record")
    assert not a.passed
    assert "56" in a.actual        # names the wrong figure, for the repair prompt


def test_truncated_table_fails():
    top5 = "\n".join(COLUMNAR.splitlines()[:8])
    res = _evaluate(top5)
    assert not res.ok
    assert not _assert_named(res, "clubs").passed


def test_only_one_atletico_fails():
    one = COLUMNAR.replace("13  Atlético Mineiro          38  13   9  16   45   49   -4   48\n", "")
    assert not _evaluate(one).ok


# --- the gate contract -------------------------------------------------------

def test_a_server_that_cannot_start_scores_zero(tmp_path, monkeypatch):
    """A dead server FAILS. It is a broken deliverable, not an unmeasurable one.

    Deliberately unlike `runtime`, which returns None when it cannot measure —
    there, "could not measure" is not "slow". Here both "answered wrongly" and
    "did not answer" are failures of the artifact. Harness faults are handled
    separately: the run pipeline aborts on them rather than recording a score.
    """
    monkeypatch.setattr(fa.rt, "_build_then_entry", lambda d, l: (None, "no entrypoint"))
    res = fa.measure(tmp_path, "python")
    assert res.score == 0.0
    assert not res.ok
    assert "no entrypoint" in res.note


def test_feedback_names_the_wrong_number_for_the_repair_attempt():
    res = _evaluate(DOUBLE_COUNTED)
    res.assertions[0].hint = "Deduplicate on (date, home, away)."
    lines = "\n".join(res.feedback_lines())
    assert "Flamengo's record" in lines
    assert "28W-6D-4L" in lines           # what was expected
    assert "Deduplicate" in lines         # how to fix it


def test_feedback_for_a_dead_server_says_to_fix_startup():
    res = fa.FactualResult(ok=False, note="did not complete the MCP handshake")
    lines = "\n".join(res.feedback_lines())
    assert "could not be started" in lines
    assert "handshake" in lines


def test_passing_result_produces_no_feedback():
    assert _evaluate(COLUMNAR).feedback_lines() == []
