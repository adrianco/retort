//! Book collection REST API backed by an embedded SQLite database.

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State, rejection::JsonRejection},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
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
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Request body for creating or replacing a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Query string for `GET /books`.
#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// Validated, normalised book fields ready for storage.
struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

/// API error that renders as `{"error": "..."}` with an appropriate status.
#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg),
            ApiError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            ApiError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        ApiError::Internal(err.to_string())
    }
}

/// Validates a request body. `title` and `author` are required and must not be blank.
fn validate(input: BookInput) -> Result<ValidBook, ApiError> {
    let title = input.title.map(|s| s.trim().to_string()).unwrap_or_default();
    let author = input.author.map(|s| s.trim().to_string()).unwrap_or_default();

    if title.is_empty() {
        return Err(ApiError::BadRequest("title is required".into()));
    }
    if author.is_empty() {
        return Err(ApiError::BadRequest("author is required".into()));
    }
    if let Some(year) = input.year {
        if year < 0 {
            return Err(ApiError::BadRequest("year must be a non-negative integer".into()));
        }
    }
    let isbn = match input.isbn.map(|s| s.trim().to_string()) {
        Some(s) if s.is_empty() => None,
        other => other,
    };
    if let Some(isbn) = &isbn {
        if !isbn.chars().all(|c| c.is_ascii_digit() || c == '-' || c == 'X' || c == 'x') {
            return Err(ApiError::BadRequest("isbn may only contain digits, '-', or 'X'".into()));
        }
    }

    Ok(ValidBook { title, author, year: input.year, isbn })
}

/// Shared application state: a single SQLite connection guarded by a mutex.
#[derive(Clone)]
pub struct AppState {
    db: Arc<Mutex<Connection>>,
}

impl AppState {
    /// Opens (or creates) the database at `path` and ensures the schema exists.
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        Self::from_connection(Connection::open(path)?)
    }

    /// Creates an in-memory database; used by tests.
    pub fn in_memory() -> rusqlite::Result<Self> {
        Self::from_connection(Connection::open_in_memory()?)
    }

    fn from_connection(conn: Connection) -> rusqlite::Result<Self> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            );",
        )?;
        Ok(Self { db: Arc::new(Mutex::new(conn)) })
    }

    fn lock(&self) -> Result<std::sync::MutexGuard<'_, Connection>, ApiError> {
        self.db
            .lock()
            .map_err(|_| ApiError::Internal("database lock poisoned".into()))
    }
}

/// Builds the application router.
pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
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

async fn create_book(
    State(state): State<AppState>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let Json(input) = body.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    let book = validate(input)?;

    let conn = state.lock()?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![book.title, book.author, book.year, book.isbn],
    )?;
    let id = conn.last_insert_rowid();
    let created = fetch(&conn, id)?.ok_or(ApiError::NotFound)?;
    Ok((StatusCode::CREATED, Json(created)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.lock()?;
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
    let conn = state.lock()?;
    fetch(&conn, id)?.map(Json).ok_or(ApiError::NotFound)
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let Json(input) = body.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    let book = validate(input)?;

    let conn = state.lock()?;
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    fetch(&conn, id)?.map(Json).ok_or(ApiError::NotFound)
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.lock()?;
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

fn fetch(conn: &Connection, id: i64) -> Result<Option<Book>, rusqlite::Error> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}
