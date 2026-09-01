# Evaluation: language=go_model=claude-opus-4-8_tooling=none · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-4-8, agent=claude-code, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all pass / 0 failed / 0 skipped (30 test functions, all effective)
- **Build:** pass — `go build ./...` clean (go 1.26, stdlib-only)
- **Lint:** pass — code_quality=0.9833 from `scores.json`
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Stored scores (`scores.json`): `test_coverage=0.625`, `defect_rate=1.0` (build+test pass), `code_quality=0.9833`, `maintainability=0.6736`, `idiomatic=0.64`, `graph_usage_score=1.0`. Verified independently: `go build ./...` succeeds and `go test ./...` reports every package `ok` (per-package coverage 59–83% where there is logic; 0% for pure type/entrypoint packages).

The port lives in a new top-level `wombat-go/` directory and is strictly additive — the Python (`blowing-off`) and TypeScript (`kittenkong`) clients and the protocol spec are untouched, satisfying the task constraints.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | inbetweenies-v2 SyncRequest/SyncResponse; reserved fields round-trip | ✓ implemented | `internal/protocol/protocol.go` — full envelopes; `VectorClock`/`Cursor` as `json.RawMessage`, round-tripped; `engine_test.go` builds/parses vs fixtures |
| R2 | Canonical version string format/parse, lexical order | ✓ implemented | `internal/version/version.go` — `canonicalLayout` emits `+00:00` no `Z`, 6-digit counter; `Timestamp` anchors on offset regex (hyphenated user id, legacy `Z` tolerated); `version_test.go` vs `version-strings.json` |
| R3 | Delta watermark = persisted server_time, exclusive `since` | ✓ implemented | `syncengine/engine.go:BuildRequest` sets `filters.since` from `Store.GetWatermark()`; `ApplyResponse` calls `SetWatermark(resp.ServerTime)`; local clock never used (comment §4 + code) |
| R4 | LWW + 1s-window version tiebreak | ✓ implemented | `internal/conflict/conflict.go:Resolve` — `abs(diff)<1000ms` → greater `version` wins, else newer `updated_at`; `conflict_test.go` from `sync-exchanges.json` tiebreak |
| R5 | Tombstone deletes | ✓ implemented | `content.deleted==true` via `EntityChange.Deleted()`/`Entity.Deleted()`; `GetActive` excludes tombstones, `GetAny` retains for sync (`graph.go`) |
| R6 | Durable local graph cache | ✓ implemented | `internal/graph/graph.go` — JSON-file store (embedded-DB-equivalent), atomic temp-file rename, reload on `Open`; `graph_test.go` persistence |
| R7 | 12 MCP tools over stdio, matching names/args | ✓ implemented | `mcp/tools_schema.go` — exactly 12 `ToolDefs` in reference order; `tools/tools.go:Execute` dispatches all 12; `server_test.go` asserts tools/list |
| R8 | Initial sync on startup + background re-sync | ✓ implemented | `cmd/wombat-mcp/main.go` — initial `engine.Sync` then `backgroundSync` on `SYNC_INTERVAL_SECONDS` ticker |
| R9 | Bearer-token auth on sync | ✓ implemented | `syncengine/engine.go:Sync` sets `Authorization: Bearer <token>`; token from `FUNKYGIBBON_AUTH_TOKEN` env |
| R10 | Passes the provided fixtures | ✓ implemented | Tests read `fixtures/{version-strings,sync-exchanges,knowledge-graph,mcp-tool-golden}.json` directly (`internal/fixtures/fixtures.go`); all packages `ok` |
| R11 | Automated tests that build and run | ✓ implemented | 30 test functions, `go test ./...` all `ok`; `test_coverage=0.625` (>0), `defect_rate=1.0` |
| R12 | README with build/test/run instructions | ✓ implemented | `wombat-go/README.md` — layout, env config, build/test/run sections |

No enhancement counted against the spec; the offline `WOMBAT_SEED` path is a beyond-spec extra (surfaced as an info finding).

## Build & Test

```text
go build ./...
(clean — exit 0)
```

```text
go test ./... -cover
ok  internal/conflict    coverage: 83.3%
ok  internal/graph       coverage: 77.7%
ok  internal/mcp         coverage: 71.4%
ok  internal/syncengine  coverage: 60.9%
ok  internal/tools       coverage: 59.3%
ok  internal/version     coverage: 75.0%
    cmd/wombat-mcp / internal/{protocol,seed,fixtures}: 0.0% (type/entrypoint-only)
```

All packages pass; 0 failures, 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test) | 1,894 |
| Lines of code (tests) | 776 |
| Files (wombat-go) | 21 (18 `.go`) |
| Dependencies | 0 (stdlib only; no `go.sum`) |
| Tests total | 30 functions |
| Tests effective | 30 (0 skipped) |
| Skip ratio | 0% |
| MCP tools | 12 (exact) |

## Findings

Top items (full list in `findings.jsonl` — all info-level; this is a clean run):

1. [info] Entrypoint (`cmd/wombat-mcp`) and `internal/seed` are untested (0% coverage)
2. [info] Sync engine coverage moderate (60.9%) — error branches lightly exercised
3. [info] Durable cache is a single JSON file (whole-file rewrite per Put) rather than an embedded DB — acceptable per R6
4. [info] Offline `WOMBAT_SEED` path is a thoughtful beyond-spec extra

## Reproduce

```bash
# code is archived as attempt.patch; apply to a scratch checkout of the-goodies
cd <scratch>
git apply /path/to/rep1/attempt.patch
cd wombat-go
go build ./...
go test ./... -cover
```
