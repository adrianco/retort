I now have full lesson content (`disclosure: "full"`, paid tier) for every category A–G and have read the entire test suite. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP Server test suite

## Overall assessment

This is a careful, genuinely impressive **unit/integration** suite — 113 green tests, fast (1.85s), deterministic, with rich domain knowledge baked into the assertions. But measured against Dave Farley's ATDD principles, which are about *acceptance tests as executable specifications*, it is structured as a set of programmer-facing correctness checks, not as specifications of user-visible behaviour run through a layered test infrastructure. There *are* acceptance- and end-to-end-flavoured tests — `tests/test_sample_questions.py` (natural-language questions → answers), `tests/test_server.py::test_stdio_subprocess_end_to_end`, and `tests/test_sdk_interop.py` — and the natural-language question table is the best thing here from an ATDD standpoint. The gap is that there is no DSL or protocol-driver layer between the tests and the system: tests hand-assemble JSON-RPC and hard-wire the exact tool names and argument shapes, which couples the "specs" to the implementation Dave spends most of the course telling you to hide.

## Strengths

- **Domain-language questions exist and are first-class.** `brsoccer/samples.py` captures real user questions — *"Who won the 2019 Brasileirão?"*, *"When did Flamengo last play Corinthians?"* — and `test_sample_questions.py` drives each one through the real MCP server (`tools/call`) and checks the answer text. That "question in the user's language → answer" shape is exactly the altitude lesson 102 ("What is an Acceptance Test?") asks for.
- **Two real end-to-end tests.** `test_stdio_subprocess_end_to_end` launches the actual server process and speaks MCP over stdin/stdout, including a deliberate malformed-line case; `test_sdk_interop.py` drives the server through the *official* MCP SDK client. Testing the deployed artefact through its real protocol is precisely the "production-like, through the natural interface" idea in lesson 202.
- **Strong determinism and isolation outcomes (lesson 302).** The SUT is a read-only dataset, tests share a session-scoped `db` fixture read-only, create no mutable state, need no teardown, and would run safely in parallel. The suite achieves the *end state* Dave wants from functional/temporal isolation.
- **No sleeps, no races, honest green build (lessons 306 & 201).** I grepped for `skip`/`xfail`/`Ignore`/`continue-on-error`/swallowed `except`/`.only` — the only skip is a legitimate `importorskip("mcp")` for an optional dependency, documented in the module docstring. Nothing is hidden; the suite tells the truth about its state.

## Priority issues

### 1. No layered test infrastructure — tests talk straight to the implementation (Architecture / DSL)

**What:** There is no test-case → DSL → protocol-driver → SUT separation. Tests either call query functions directly (`tests/test_queries.py:12` `q.search_matches(team="Flamengo", ...)`) or hand-build raw JSON-RPC envelopes inline and call `server.handle(...)`. The end-to-end test constructs the wire messages by hand and parses stdout line-by-line (`test_server.py:99-117`). The one piece of reuse is the 3-line `rpc()` helper (`test_server.py:16-20`).

**Why it matters:** Lesson 305 ("The Four Layer Model") and lesson 301 ("Building a DSL") make the layering the load-bearing idea: the test case speaks the domain, the DSL provides a stable vocabulary with defaults and aliasing, and *only* the protocol driver knows how the system is actually reached. Lesson 203's "Common Mistake 3: No Reuse in the DSL" names this directly — *"they are implementing nearly every spec from scratch… if you can't see a need for reuse, you are not thinking in terms of the problem domain."* Every sample-question test re-implements the same `tools/call` plumbing.

**Before** (`test_sample_questions.py:28-38`, plumbing in the test):
```python
resp = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                      "params": {"name": tool, "arguments": args}})
text = resp["result"]["content"][0]["text"]
assert result["isError"] is False, text
for snippet in expected:
    assert snippet in text
```

**After** — a thin DSL over a protocol driver, so the spec says only *what*:
```python
# protocol driver: the ONLY place that knows about JSON-RPC envelopes / stdio / the SDK
class McpDriver:
    def ask(self, tool, **args) -> str:
        resp = self._server.handle({"jsonrpc": "2.0", "id": self._next_id(),
                                    "method": "tools/call",
                                    "params": {"name": tool, "arguments": args}})
        result = resp["result"]
        assert not result["isError"], result["content"][0]["text"]   # assertion lives in the PD
        return result["content"][0]["text"]

# DSL: domain vocabulary with defaults
class Soccer:
    def head_to_head(self, a, b, season=None): ...
    def standings(self, season, top=20): ...

# test case: pure domain language
def test_2019_champion(soccer):
    soccer.standings(2019).should_name_champion("Flamengo")
```
The same `McpDriver` interface could then back both the in-process and the subprocess/SDK channels — lesson 303's "one interface, many drivers" — collapsing `test_sample_questions`, the subprocess e2e, and `test_sdk_interop` onto *one* set of specs run through three drivers.

### 2. The acceptance specs are coupled to the implementation they should hide (Spec quality)

**What:** Each entry in `samples.CASES` pins not just the question and expected answer but the exact **tool name** and **argument dict** the server must receive — e.g. `("Which team scored the most goals in Serie A 2023?", "team_rankings", {"metric": "goals_for", "season": 2023, "limit": 1}, ["1. Grêmio - goals for: 63"])`. The docstring even calls these "the tool call an LLM would make," but no LLM is involved — the routing is hard-coded, so the spec asserts *how* the system is driven rather than *what* the user gets.

**Why it matters:** This is lesson 103b's calculator and lesson 203's login example almost exactly. *"I enter 'scott' into the 'username' field… I click 'login'"* leaks implementation; *"When I log in correctly, then I can access my accounts"* does not. Here `"team_rankings", {"metric": "goals_for", "limit": 1}` is the equivalent leak — it bakes in the tool catalogue and parameter names. Dave's coupling test (lesson 203): *imagine the spec fulfilled by a completely different system.* If you renamed `team_rankings` to `rankings` or restructured its arguments, every sample "spec" breaks even though the user-visible behaviour is unchanged — the opposite of the durability lessons 102/202 promise.

**Before:**
```python
("Which team scored the most goals in Serie A 2023?",
 "team_rankings", {"metric": "goals_for", "season": 2023, "limit": 1},
 ["1. Grêmio - goals for: 63"]),
```
**After** — the spec holds the question and the outcome; the DSL/driver owns tool selection and argument shape:
```python
("Which team scored the most goals in Serie A 2023?",
 expect(answer_names="Grêmio", answer_contains="63 goals")),
```
(The mapping of question → tool now lives once, in the driver — the single place lesson 202 says SUT-shape changes should be absorbed.)

### 3. Wall-clock timing baked into acceptance tests — environment-sensitive flakiness + conflated concerns (Intermittency)

**What:** `test_sample_questions.py:30-38` asserts correctness **and** `elapsed < 2.0` in the same test, and `test_performance.py` is built entirely on `assert timed(...) < 2.0 / < 5.0`, including a cold-load `< 5.0`.

**Why it matters:** Lesson 306 lists "changes in the environment" and "resource contention" as two of the five root causes of intermittency — and absolute wall-clock thresholds are the textbook trigger: the same code that passes on a quiet laptop will go red on a loaded CI box or a noisy shared runner, with nothing actually broken. That erodes exactly the trust lesson 306 is about ("when a test fails, we can trust the failure and reject the change"). It also violates lesson 202's "assert a single outcome / two reasons to fail": a sample-question test that fails *could* mean the answer is wrong *or* the machine was busy — you can't tell which from the failure.

**Fix:** Separate the concerns. Keep the sample-question tests purely about the answer (drop the `elapsed` assert). Move performance to its own non-gating budget check that reports a number rather than flipping a build red on a slow host — a regression trend, not a pass/fail gate wired into the acceptance suite.

## Further improvements

- **Exact-string answer assertions are brittle (durability, lessons 102/202).** `test_queries.py:13` asserts `r["text"].startswith("Flamengo vs Fluminense (Fla-Flu derby):")` and many tests pin whole formatted sentences incl. the `(28W, 6D, 4L` fragment. A cosmetic wording change to the answer formatter breaks specs without any behaviour change. Prefer asserting the *facts* the answer must convey over its exact typography.
- **No CI pipeline present (lesson 201).** There's no `.github/` or equivalent. Lesson 201 frames acceptance tests as the releasability gate; without a pipeline running them, that gate isn't actually in place. Worth adding even a minimal one.
- **The one end-to-end SDK test is silently skipped here.** `importorskip("mcp")` is defensible for an optional dep, but in this environment `mcp` isn't installed, so your *only* real-SDK interop path doesn't run and the build still shows green (lesson 201's visibility concern). Consider making the SDK a test dependency so the e2e path actually executes, or tracking it explicitly rather than as a quiet skip.
- **Isolation is "free" today but undefended.** Determinism here rests on the SUT being read-only (lesson 302). Fine now — just note that the moment any write path is added, the shared session-scoped `db` and absence of functional/temporal aliasing would become a real leakage risk.

## Suggested next steps

1. **Introduce the two missing layers**, even for a read-only system: a `McpDriver` (the one place that knows JSON-RPC/stdio/SDK, with the `isError` assertion inside it) and a small `Soccer` DSL with domain methods and defaults. This is the highest-leverage change — it unlocks issues #1 and #2 at once and lets the in-process, subprocess, and SDK channels share one set of specs (lesson 303).
2. **Decouple the sample-question specs** from tool names/argument dicts so they assert question → outcome only (lesson 203's coupling test).
3. **Pull timing out of the acceptance path** — answers and speed are two different questions (lessons 306, 202).

Then keep what's already strong: the natural-language question corpus, the real-process end-to-end coverage, and the honest green build.

*(Review grounded in the full ATDD course lessons: 102, 103b, 201, 202, 203, 301, 302, 303, 305, 306 — fetched complete, paid tier.)*

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 3, "D": 1, "E": 2, "F": 2, "G": 3}, "disclosure": "full"}
```