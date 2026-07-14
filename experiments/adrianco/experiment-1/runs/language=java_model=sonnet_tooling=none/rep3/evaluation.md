# Evaluation: language=java_model=sonnet_tooling=none · rep 3

## Summary

- **Factors:** language=java, model=sonnet, tooling=none
- **Status:** cannot-verify (archive incomplete — no Java source files; DB scores indicate test_coverage=1.0, code_quality=1.0)
- **Requirements:** 1/12 implemented, 11 partial (cannot-verify — source missing from archive), 0 missing
- **Tests:** 0 in archive / DB test_coverage=1.0 (README claims 12 integration tests)
- **Build:** pass per DB (defect_rate=1.0) — archive has no source to compile
- **Lint:** pass per DB (code_quality=1.0) — no source to lint in archive
- **Architecture:** summary skill unavailable
- **Findings:** 12 items in `findings.jsonl` (1 critical, 10 high, 1 medium)

**Note:** retort.db scores (test_coverage=1.0, code_quality=1.0, defect_rate=1.0, idiomatic=0.88, maintainability=0.96) indicate the agent generated a fully working implementation that passed all tests. However, the archive contains zero `.java` source files — only build scaffolding (pom.xml, application.properties) and documentation (README.md). This evaluation cannot perform source-level requirement verification. All requirement assessments below are `cannot-verify` except R11 (README.md).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ? cannot-verify | No .java source in archive; README.md:32-40 describes endpoint; DB test_coverage=1.0 |
| R2 | GET /books lists all books | ? cannot-verify | No .java source in archive; README.md:44-49 describes endpoint; DB test_coverage=1.0 |
| R3 | GET /books ?author= filter | ? cannot-verify | No .java source in archive; README.md:47 describes filter; DB test_coverage=1.0 |
| R4 | GET /books/{id} single book | ? cannot-verify | No .java source in archive; README.md:53-57 describes endpoint; DB test_coverage=1.0 |
| R5 | PUT /books/{id} updates a book | ? cannot-verify | No .java source in archive; README.md:61-69 describes endpoint; DB test_coverage=1.0 |
| R6 | DELETE /books/{id} deletes a book | ? cannot-verify | No .java source in archive; README.md:73-77 describes endpoint; DB test_coverage=1.0 |
| R7 | Data stored in SQLite | ? cannot-verify | pom.xml:39 sqlite-jdbc dep; application.properties:1 jdbc:sqlite config; no @Entity source |
| R8 | JSON responses with HTTP status codes | ? cannot-verify | No .java source in archive; README.md describes 201/200/400/404/204 codes; DB test_coverage=1.0 |
| R9 | Input validation: title and author required | ? cannot-verify | pom.xml:33 spring-boot-starter-validation dep; no @Valid source; DB test_coverage=1.0 |
| R10 | GET /health endpoint | ? cannot-verify | No .java source in archive; README.md:28-30 describes /health; DB test_coverage=1.0 |
| R11 | README.md with setup/run instructions | ✓ implemented | README.md present with build, run, and API documentation |
| R12 | At least 3 unit/integration tests | ? cannot-verify | No src/test/java/; README.md:87 claims 12 tests; DB test_coverage=1.0 |

## Build & Test

### Build (from DB scores)
```text
DB scores (retort.db): test_coverage=1.0, defect_rate=1.0, code_quality=1.0
These confirm build + all tests passed at scoring time.

Archive state: No .java files present — only scaffolding.
  - pom.xml: Spring Boot 3.2.4 with sqlite-jdbc, JPA, validation dependencies
  - src/test/resources/application.properties: SQLite in-memory config for tests
  - README.md: Describes 5 CRUD endpoints + health check + 12 integration tests
```

### Tests (from DB scores)
```text
DB test_coverage=1.0 — build + all tests passed at scoring time.
No test source files in archive (src/test/java/ absent).
README.md claims 12 integration tests covering all endpoints, validation, filtering, error cases.
Cannot independently verify test count or coverage from archive.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (Java — not archived) |
| Lines of config/docs | 154 (pom.xml: 62, README.md: 87, application.properties: 5) |
| Files (archived) | 6 (pom.xml, README.md, TASK.md, stack.json, _meta.json, application.properties) |
| Dependencies | 6 (spring-boot-starter-web, data-jpa, validation, sqlite-jdbc, hibernate-community-dialects, spring-boot-starter-test) |
| Tests total | unknown (12 per README; 0 in archive) |
| Tests effective | unknown |
| Skip ratio | N/A |
| Build duration | N/A |
| DB test_coverage | 1.0 |
| DB code_quality | 1.0 |
| DB idiomatic | 0.88 |
| DB maintainability | 0.96 |
| DB token_efficiency | 0.5 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Archive missing all Java source files — cannot verify implementation
2. [high] POST /books — cannot verify from archive; DB test_coverage=1.0 suggests implemented
3. [high] GET /books — cannot verify from archive; DB test_coverage=1.0 suggests implemented
4. [high] GET /books ?author= filter — cannot verify from archive
5. [high] GET /books/{id} — cannot verify from archive

## Reproduce

```bash
cd experiment-1/runs/language=java_model=sonnet_tooling=none/rep3
find src -type f -name "*.java"                    # confirms zero Java files
find src -type f                                    # only src/test/resources/application.properties
cat pom.xml                                         # Spring Boot scaffolding present
cat README.md                                       # describes full API + 12 tests
cat src/test/resources/application.properties       # SQLite config present
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='java' AND json_extract(er.run_config_json,'$.model')='sonnet' AND json_extract(er.run_config_json,'$.tooling')='none' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
