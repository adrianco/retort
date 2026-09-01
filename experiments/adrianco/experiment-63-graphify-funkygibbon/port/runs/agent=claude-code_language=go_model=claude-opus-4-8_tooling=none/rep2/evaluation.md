# Evaluation: go · claude-code · claude-opus-4-8 · tooling=none · rep 2

## Summary

- **Factors:** language=go, model=claude-opus-4-8, agent=claude-code, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 17 test functions, 0 skipped (17 effective) — all pass
- **Build:** pass (from `scores.json`: `defect_rate=1.0` ⇒ build + tests succeeded)
- **Lint:** pass — `code_quality=0.983`, `idiomatic=0.82`
- **Architecture:** source archived as `attempt.patch` only (no laid-out tree in run_dir); `run-summary` skipped — see note below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

Strong, spec-faithful port. The agent added a new top-level `wombat-go/`
directory (17 Go files, ~2683 LOC) implementing inbetweenies-v2 end to end, and
did not touch the Python/TypeScript clients or the protocol spec — matching the
additive constraint. Stored scores: `test_coverage=0.601`, `code_quality=0.983`,
`maintainability=0.565`, `idiomatic=0.82`, `graph_usage_score=1.0`,
`defect_rate=1.0`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | inbetweenies-v2 SyncRequest/SyncResponse, reserved fields round-trip | ✓ implemented | `internal/model/model.go` — `SyncRequest`/`SyncResponse`; `VectorClock`/`Cursor` as `json.RawMessage` (byte round-trip) |
| R2 | Canonical version strings: format/parse, lexical order | ✓ implemented | `internal/version/version.go` — `canonicalLayout` (`+00:00`, no Z), `Parse` anchors on offset regex (legacy Z + hyphenated user id), `Compare`/`Greater` lexical; `version_test.go` asserts `version-strings.json` |
| R3 | Delta watermark: persist server_time, exclusive `since`; never client clock | ✓ implemented | `internal/sync/sync.go` — `BuildRequest` replays `Marks.Get()` into `filters.since`; `ApplyResponse` advances only after successful apply; `store/watermark.go` FileStore persists |
| R4 | Conflict LWW + 1s-window version tiebreak | ✓ implemented | `internal/sync/conflict.go` — `Resolve`: `abs(diff)<1000ms` ⇒ `version.Greater` wins (not sync_id); `sync_test.go` covers the fixture case |
| R5 | Tombstone deletes | ✓ implemented | `model.go` `Entity.Deleted()` reads `content.deleted`; graph retains tombstones, golden test asserts tombstone exclusion from queries |
| R6 | Durable local graph cache | ✓ implemented | `internal/graph/graph.go` — `Open`/`Save` JSON file with atomic `.tmp`+rename; persisted on every mutation; survives restart |
| R7 | MCP stdio server, exactly the 12 named tools | ✓ implemented | `internal/mcp/tools.go` registers all 12 names; `server.go` line-delimited JSON-RPC over stdin/stdout (`tools/list`, `tools/call`) |
| R8 | Initial sync on startup + background re-sync | ✓ implemented | `cmd/wombat/main.go` — best-effort initial `Sync`, then `go backgroundSync` on `SYNC_INTERVAL_SECONDS` ticker |
| R9 | Bearer-token auth on sync | ✓ implemented | `sync.go` `post()` sets `Authorization: Bearer <token>`; token from `FUNKYGIBBON_AUTH_TOKEN` env |
| R10 | Passes provided fixtures | ✓ implemented | `version_test.go`, `sync_test.go`, `golden_test.go` load `version-strings.json`, `sync-exchanges.json`, `mcp-tool-golden.json`, `knowledge-graph.json` via `testsupport.Dir`; tests pass (see info finding on assertion depth) |
| R11 | Automated tests that build+run | ✓ implemented | 17 `Test*` funcs across version/sync/graph/mcp; `test_coverage=0.601` > 0, `defect_rate=1.0` |
| R12 | README with build/test/run | ✓ implemented | `wombat-go/README.md` — Build, Test, Run (env table incl. `FUNKYGIBBON_AUTH_TOKEN`), `mcpServers` entry, 12-tool list |

## Build & Test

Not re-run — stored mechanical scores used per skill (evaluate-run §2).

```text
scores.json: defect_rate=1.0  ⇒ build + tests succeeded
scores.json: test_coverage=0.601  (coverage fraction; tests executed)
17 Test* functions, 0 t.Skip/t.Skipf occurrences
```

Toolchain present for reference (go1.26.6 darwin/arm64); patch applies cleanly
to a fresh tree.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, source+tests) | 2683 |
| Go files | 17 |
| Dependencies | 0 (stdlib only; `go.mod` module + `go 1.26`) |
| Tests total | 17 funcs |
| Tests effective | 17 (0 skipped) |
| Skip ratio | 0% |
| Test coverage | 60.1% |
| Largest file | `internal/graph/graph.go` (604 lines) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] `graph.go` is 604 lines, over the ~500-line guideline (maintainability=0.565)
2. [info] Golden tests assert essential outcomes (entity IDs, tombstone exclusion) rather than byte-exact fixture reproduction
3. [info] 60.1% coverage leaves the HTTP round-trip and stdio framing paths only indirectly exercised

No critical or high findings — the run fully implements the spec and all tests pass.

## Notes

- **`run-summary` skipped:** the archive stores generated code only as
  `attempt.patch`; there is no laid-out source tree inside `run_dir` for the
  summary skill to analyze, and writing a reconstructed tree into `run_dir`
  would violate the read-only constraint. Architecture is described inline in
  the Requirements table instead.

## Reproduce

```bash
# Inspect the generated code (archive stores it as a patch):
cd <scratch>
git init -q && git apply <run_dir>/attempt.patch
cd wombat-go
go build ./...
go test ./...            # 17 tests pass; fixtures loaded from repo-root fixtures/

# Mechanical scores (already computed, do not re-run in the gate):
cat <run_dir>/scores.json
```
