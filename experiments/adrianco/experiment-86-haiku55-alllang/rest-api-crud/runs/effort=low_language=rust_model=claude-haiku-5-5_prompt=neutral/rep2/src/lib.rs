//! Book collection REST API backed by SQLite.

use std::sync::{Arc, Mutex, MutexGuard};

use axum::{
    body::Bytes,
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::json;

/// A book as stored and returned by the API.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Raw request body for create and update. Validation happens in `validate`.
#[derive(Debug, Deserialize)]
struct BookInput {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

/// Validated, normalised book fields ready to be stored.
#[derive(Debug, PartialEq)]
struct BookFields {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ListQuery {
    author: Option<String>,
}

/// Errors returned to clients as `{"error": "..."}`.
#[derive(Debug)]
pub enum ApiError {
    /// Malformed JSON or wrong field types.
    BadRequest(String),
    /// Well-formed request that fails field validation.
    Validation(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::Validation(m) => (StatusCode::UNPROCESSABLE_ENTITY, m),
            ApiError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        ApiError::Internal(format!("database error: {err}"))
    }
}

#[derive(Clone)]
struct AppState {
    db: Arc<Mutex<Connection>>,
}

impl AppState {
    fn conn(&self) -> Result<MutexGuard<'_, Connection>, ApiError> {
        self.db
            .lock()
            .map_err(|_| ApiError::Internal("database lock poisoned".to_string()))
    }
}

/// Creates the books table if it does not already exist.
pub fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
}

/// Builds the router, initialising the schema on the given connection.
pub fn app(conn: Connection) -> rusqlite::Result<Router> {
    init_schema(&conn)?;
    let state = AppState {
        db: Arc::new(Mutex::new(conn)),
    };
    Ok(Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state))
}

/// Parses and validates a request body. `title` and `author` are required;
/// `year` and `isbn` are optional.
fn validate(body: &[u8]) -> Result<BookFields, ApiError> {
    let input: BookInput = serde_json::from_slice(body)
        .map_err(|e| ApiError::BadRequest(format!("invalid JSON body: {e}")))?;

    let title = required(input.title, "title")?;
    let author = required(input.author, "author")?;

    if let Some(year) = input.year {
        if year <= 0 {
            return Err(ApiError::Validation("year must be a positive number".to_string()));
        }
    }

    let isbn = input
        .isbn
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty());

    Ok(BookFields {
        title,
        author,
        year: input.year,
        isbn,
    })
}

fn required(value: Option<String>, field: &str) -> Result<String, ApiError> {
    match value.map(|v| v.trim().to_string()) {
        Some(v) if !v.is_empty() => Ok(v),
        _ => Err(ApiError::Validation(format!("{field} is required"))),
    }
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

fn fetch_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(state): State<AppState>,
    body: Bytes,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let fields = validate(&body)?;
    let conn = state.conn()?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![fields.title, fields.author, fields.year, fields.isbn],
    )?;
    let book = fetch_book(&conn, conn.last_insert_rowid())?
        .ok_or_else(|| ApiError::Internal("inserted book not found".to_string()))?;
    Ok((StatusCode::CREATED, Json(book)))
}

/// Lists books. `?author=` filters by exact, case-insensitive author name.
async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.conn()?;
    let books = match query.author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books
                 WHERE author = ?1 COLLATE NOCASE ORDER BY id",
            )?;
            let rows = stmt.query_map(params![author.trim()], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
    };
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = state.conn()?;
    fetch_book(&conn, id)?
        .map(Json)
        .ok_or(ApiError::NotFound)
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    body: Bytes,
) -> Result<Json<Book>, ApiError> {
    let fields = validate(&body)?;
    let conn = state.conn()?;
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![fields.title, fields.author, fields.year, fields.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    fetch_book(&conn, id)?
        .map(Json)
        .ok_or(ApiError::NotFound)
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.conn()?;
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_accepts_minimal_book() {
        let fields = validate(br#"{"title":"Dune","author":"Frank Herbert"}"#).unwrap();
        assert_eq!(
            fields,
            BookFields {
                title: "Dune".into(),
                author: "Frank Herbert".into(),
                year: None,
                isbn: None,
            }
        );
    }

    #[test]
    fn validate_trims_and_drops_blank_isbn() {
        let fields = validate(
            br#"{"title":"  Dune ","author":" Frank Herbert","isbn":"   "}"#,
        )
        .unwrap();
        assert_eq!(fields.title, "Dune");
        assert_eq!(fields.author, "Frank Herbert");
        assert_eq!(fields.isbn, None);
    }

    #[test]
    fn validate_rejects_missing_or_blank_title_and_author() {
        assert!(matches!(
            validate(br#"{"author":"A"}"#),
            Err(ApiError::Validation(m)) if m == "title is required"
        ));
        assert!(matches!(
            validate(br#"{"title":"T","author":"   "}"#),
            Err(ApiError::Validation(m)) if m == "author is required"
        ));
    }

    #[test]
    fn validate_rejects_malformed_json_and_bad_year() {
        assert!(matches!(validate(b"{not json"), Err(ApiError::BadRequest(_))));
        assert!(matches!(
            validate(br#"{"title":"T","author":"A","year":"1965"}"#),
            Err(ApiError::BadRequest(_))
        ));
        assert!(matches!(
            validate(br#"{"title":"T","author":"A","year":0}"#),
            Err(ApiError::Validation(_))
        ));
    }
}
