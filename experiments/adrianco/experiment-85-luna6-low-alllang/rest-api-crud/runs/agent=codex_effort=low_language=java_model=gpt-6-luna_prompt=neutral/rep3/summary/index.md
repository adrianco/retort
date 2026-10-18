# Codebase summary — book-collection (Java / Spring Boot)

Direct summary (run-summary skill not invoked via Skill tool in this non-interactive
session; codebase is small — 156 LOC across 6 files — so summarized inline).

## Stack
- Java 17, Spring Boot 3.3.5 (`spring-boot-starter-web`, `-validation`, `-jdbc`)
- Persistence: SQLite via `org.xerial:sqlite-jdbc` + `JdbcTemplate` (no JPA)
- Build: Maven (`spring-boot-starter-parent`)

## Modules
| File | Role |
|------|------|
| `BookApplication.java` | `@SpringBootApplication` entry point; a `CommandLineRunner` creates the `books` table (`id INTEGER PK AUTOINCREMENT, title/author NOT NULL, year, isbn`) on startup. |
| `Book.java` | Immutable `record Book(Long id, String title, String author, Integer year, String isbn)` — the persistence/response shape. |
| `BookRequest.java` | `record BookRequest` with `@NotBlank` on `title` and `author` — the request/validation shape. |
| `BookController.java` | `@RestController` holding all 6 routes + `/health`, a shared `RowMapper<Book>`, and a private `find(id)` that throws `ResponseStatusException(404)` when absent. |
| `application.properties` | JDBC URL (`BOOKS_DB_URL` overridable), SQLite driver, `spring.sql.init.mode=never`. |
| `BookApiTest.java` | 4 `@SpringBootTest` + `MockMvc` integration tests against a shared in-memory SQLite DB. |

## Request flow
HTTP → `BookController` route → `JdbcTemplate` (parameterized SQL) → SQLite.
Create uses a `GeneratedKeyHolder` to return the new row; reads/updates/deletes
funnel missing-id cases through `find(id)` → 404. Validation failures on
`@Valid BookRequest` surface as Spring's default 400.

## Notable design point (see findings)
Tests share one in-memory SQLite DB across methods and reset state with
`DELETE FROM books` in `@BeforeEach`. Because `AUTOINCREMENT` sequence state is
**not** cleared by `DELETE`, the hardcoded `/books/1` assertions are order-fragile.
