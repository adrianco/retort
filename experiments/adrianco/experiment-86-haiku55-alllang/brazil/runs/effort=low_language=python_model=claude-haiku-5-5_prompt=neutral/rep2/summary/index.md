# Architecture Summary — brazilian-soccer MCP server

A clean 4-layer Python package (`soccer_mcp/`, 1683 LoC incl. tests) that serves the
Kaggle Brazilian-soccer datasets over the MCP protocol. (`run-summary` skill is not
registered as an invocable skill in this harness; this summary was written inline.)

## Modules

| Module | Role |
|--------|------|
| `normalize.py` (182 L) | Pure helpers: team-name canonicalisation (state suffixes, accents, club-word stripping, aliases), competition-key resolution from free text, multi-format date parsing. `TeamRef` NamedTuple is the comparable club identity. |
| `loader.py` (263 L) | Reads all 6 CSVs into frozen `Match`/`Player` dataclasses, de-duplicates overlapping match rows across sources (`_same_match` on competition+score+±1 day+club-token overlap), returns a `Dataset`. |
| `queries.py` (450 L) | `SoccerQueries` — the query layer. Match search (team/opponent/venue/season/date/competition), head-to-head, team record, standings (3-1-0 pts), league stats, biggest wins, venue leaderboard, player search (name/nationality/club/position-group/rating), Brazilian-players-by-club. Returns plain Python data. |
| `formatting.py` (151 L) | Renders query results into the spec's plain-text answer format. |
| `server.py` (155 L) | `FastMCP` server exposing 11 `@mcp.tool()` handlers; errors returned as text so the LLM can self-correct. `python -m soccer_mcp` entrypoint. |

## Data flow

`load_dataset()` → `Dataset(matches, players)` → injected into `SoccerQueries` →
wrapped by `create_server()` as MCP tools → `formatting.*` → text answer.

## Layering

Clean dependency direction: `server → formatting/queries → loader → normalize`. The
query layer is deliberately pure (no MCP/IO coupling), which is why the 59-case test
suite can exercise it directly against the real data as well as through the tool layer.

## Tests

`tests/` — pytest with Given/When/Then BDD comments. `conftest.py` loads the real
dataset once per session and exposes `queries`, `server` and a `call(tool, **args)`
helper. 59 test cases (42 functions, parametrised), covering loader dedup, normalisation,
every query function, and every MCP tool end-to-end incl. the spec's 2019-champion example.
