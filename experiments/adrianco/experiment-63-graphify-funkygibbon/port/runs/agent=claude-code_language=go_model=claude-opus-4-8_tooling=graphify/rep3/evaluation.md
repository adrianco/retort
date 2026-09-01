# Evaluation: language=go model=claude-opus-4-8 tooling=graphify · rep 3

## Summary

- **Factors:** language=go, model=claude-opus-4-8, agent=claude-code, tooling=graphify
- **Status:** ok — additive Go port `wombat-go/`, build + all tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all pass / 0 failed / 0 skipped (33 test functions, statement coverage 64.9%)
- **Build:** pass — `test_coverage=0.649`, `defect_rate=1.0` from `scores.json` (build+test gate)
- **Lint:** pass — `code_quality=0.983` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session; module map summarised inline below
- **Findings:** 9 items in `findings.jsonl` (0 critical, 0 high, 1 low, 8 info) — one boundary nit (`R4`), rest are enhancements/observations, no defects

Scores read from `{run_dir}/scores.json` (inline gate output — no re-run of the toolchain):
`code_quality=0.983`, `test_coverage=0.649`, `defect_rate=1.0`, `maintainability=0.731`,
`idiomatic=0.84`, `graph_usage_score=1.0`, `token_efficiency=0.0059`.

This is a clean, high-quality run: a spec-faithful, dependency-free Go port that reproduces the
shared conformance fixtures and passes its own suite. The port directory is `wombat-go/` (rep1
used `eckythump-go/`, rep2 `goanna/` — the agent renames per replicate).

## Requirements

Pinned checklist from `../../REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | inbetweenies-v2 SyncRequest/SyncResponse, reserved fields round-trip | ✓ implemented | `wombat-go/internal/protocol/protocol.go` — full `SyncRequest`/`SyncResponse`; `VectorClock`/`Cursor` kept as `json.RawMessage`; `engine.go` stashes+replays them; `protocol_test.go` |
| R2 | Canonical version strings, lexical order | ✓ implemented | `wombat-go/internal/version/version.go` — `FormatTimestamp` emits `+00:00` no `Z`, `Format`=`{ts}-{counter:06d}-{user}`, `Compare`/`Greater` lexical; `tsPrefix` regex tolerates legacy Z + hyphenated user id; `version_test.go` asserts `version-strings.json` |
| R3 | Delta watermark = server_time, exclusive since, never client clock | ✓ implemented | `wombat-go/internal/sync/engine.go:BuildRequest` sends persisted `server_time` as `filters.since`; `Sync` stores `resp.ServerTime` via `Watermark.Store`; exclusivity is server-side (see finding `watermark-exclusivity-clientside`); `exclusive_test.go` |
| R4 | LWW + 1s-window version tiebreak | ✓ implemented | `wombat-go/internal/protocol/conflict.go:Resolve` — `abs(diffMS) < 1000` → lexically greater `Version` wins; else newer `updated_at`; `conflict_test.go`. Boundary nit: window is strict `<` (finding `R4-window-boundary`) |
| R5 | Tombstone deletes | ✓ implemented | `wombat-go/internal/model/model.go:Deleted` (content.deleted==true); `store.go` retains tombstones but `GetActiveEntity`/`ActiveEntities` exclude them; graph tools filter to active; `store_test.go:TestSeedAndTombstone` |
| R6 | Durable local graph cache, survives restart | ✓ implemented | `wombat-go/internal/store/store.go` — atomic JSON snapshot (`WriteFile`+`Rename`), reloaded in `Open`; entities+relationships persisted; `store_test.go:TestDurabilityAcrossReopen` |
| R7 | MCP server exposes all 12 named tools over stdio | ✓ implemented | `wombat-go/internal/mcp/server.go` (JSON-RPC 2.0 line framing, `tools/list`+`tools/call`); `schemas.go:toolSchemas` — all 12 names present with required args (grep → 12); `server_test.go:TestToolsListHas12` |
| R8 | Initial sync on startup + background re-sync | ✓ implemented | `wombat-go/cmd/wombat-mcp/main.go:run` — initial `engine.Sync` then `go func` with `SYNC_INTERVAL_SECONDS` ticker |
| R9 | Bearer-token auth on sync requests | ✓ implemented | `wombat-go/internal/sync/transport.go:HTTPTransport.Sync` sets `Authorization: Bearer <token>`; token from `FUNKYGIBBON_AUTH_TOKEN` env in `main.go` |
| R10 | Passes provided fixtures | ✓ implemented | `internal/mcp/golden_test.go:TestMCPToolGoldenFixture` drives `mcp-tool-golden.json` on the `knowledge-graph.json` seed; `sync/engine_test.go` exercises `sync-exchanges.json`; `version_test.go` asserts `version-strings.json`; all four fixtures referenced |
| R11 | Automated tests that build+run | ✓ implemented | 33 `Test*` funcs across 6 packages; `test_coverage=0.649 (>0)`, `defect_rate=1.0`; 0 `t.Skip` |
| R12 | README with build/test/run instructions | ✓ implemented | `wombat-go/README.md` — layout, build/test/run, env config table; `main.go` header documents env config |

## Build & Test

Not re-run — stored gate scores used (skill step 2).

```text
scores.json: {"test_coverage": 0.649, "defect_rate": 1.0, "code_quality": 0.983,
              "maintainability": 0.731, "idiomatic": 0.84, "graph_usage_score": 1.0}
# test_coverage 0.649 = 64.9% statement coverage; defect_rate 1.0 = go build + go test both passed
```

```text
go test ./...   (as run by retort's scorer)
33 Test* functions, 0 t.Skip; defect_rate=1.0 => build+test green
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, impl only) | 1,923 |
| Lines of code (Go, tests) | 1,029 |
| Files (wombat-go, all) | 24 |
| Go files | 22 |
| Dependencies (external) | 0 (pure stdlib) |
| Tests total (funcs) | 33 |
| Tests effective (passed+failed) | 33 |
| Skip ratio | 0% |
| Statement coverage | 64.9% |

## Findings

Top 5 by severity (full list in `findings.jsonl` — one low boundary nit, rest enhancements/observations, no defects):

1. [low] Conflict 1s tiebreak window is strict `<` (`internal/protocol/conflict.go:Resolve`) — an exactly-1000ms diff falls to LWW instead of the version tiebreak; untested by the fixtures. Same edge as rep2.
2. [info] Durable cache rewrites the whole JSON snapshot on every mutation (`internal/store/store.go:saveLocked`) — O(n) I/O per row change; fine at fixture scale, satisfies R6.
3. [info] Version counter is process-monotonic mod 1e6, not the reference perf-counter (`internal/version/version.go:New`) — output still matches `version-strings.json`.
4. [info] Exclusive-since (R3) sent verbatim; strict-greater comparison is server-side (`internal/sync/engine.go`) — correct for a client port; local clock is never the watermark.
5. [info] Statement coverage 64.9% — tool error branches and background re-sync unexercised; R11 still passes.

## Reproduce

```bash
run="experiments/adrianco/experiment-63-graphify-funkygibbon/port/runs/agent=claude-code_language=go_model=claude-opus-4-8_tooling=graphify/rep3"
cat "$run/scores.json"                       # stored build/test/lint gate scores (no re-run)
cat "$run/../../REQUIREMENTS.json"           # pinned 12-requirement checklist
# generated code lives inside attempt.patch under wombat-go/ (all new files); extract the '+' lines
# of each `+++ b/wombat-go/...` hunk to reconstruct the tree, then:
grep -oE '"(search_entities|get_entity_details|create_entity|update_entity|create_relationship|get_devices_in_room|find_device_controls|get_room_connections|find_path|find_similar_entities|get_procedures_for_device|get_automations_in_room)"' wombat-go/internal/mcp/schemas.go | sort -u | wc -l  # -> 12
grep -rhE '^func Test' wombat-go --include='*_test.go' | wc -l   # -> 33
```
