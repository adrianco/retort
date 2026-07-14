//! Book collection REST API.
//!
//! Built with [`axum`] for routing and [`rusqlite`] (bundled SQLite) for storage.
//! The public entry points are [`init_db`], which prepares a connection, and
//! [`app`], which builds the router around a shared connection.

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::json;

/// Shared application state: a SQLite connection guarded by a mutex.
pub type AppState = Arc<Mutex<Connection>>;

/// A book record as stored and returned by the API.
#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    /// Publication year. Optional.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i64>,
    /// ISBN. Optional.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub isbn: Option<String>,
}

/// Payload accepted when creating or replacing a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Query parameters for listing books.
#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// A simple JSON error wrapper with an associated HTTP status code.
pub struct ApiError {
    status: StatusCode,
    message: String,
}

impl ApiError {
    fn new(status: StatusCode, message: impl Into<String>) -> Self {
        Self {
            status,
            message: message.into(),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.status, Json(json!({ "error": self.message }))).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, format!("database error: {err}"))
    }
}

/// Create a connection and ensure the `books` table exists.
///
/// Pass `":memory:"` for an in-memory database (useful for tests) or a file
/// path for persistent storage.
pub fn init_db(path: &str) -> Result<Connection, rusqlite::Error> {
    let conn = Connection::open(path)?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
        [],
    )?;
    Ok(conn)
}

/// Build the application router around a shared connection.
pub fn app(conn: Connection) -> Router {
    let state: AppState = Arc::new(Mutex::new(conn));
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

/// Validate and normalise the required fields, returning trimmed values.
fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();
    if title.is_empty() {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            "title is required and must not be empty",
        ));
    }
    if author.is_empty() {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            "author is required and must not be empty",
        ));
    }
    Ok((title, author))
}

/// GET /health
async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

/// POST /books
async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author) = validate(&input)?;
    let conn = state.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();
    let book = Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    Ok((StatusCode::CREATED, Json(book)))
}

/// GET /books (optional `?author=` filter)
async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.lock().unwrap();
    let books = match query.author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map([author], row_to_book)?;
            rows.collect::<Result<Vec<_>, _>>()?
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect::<Result<Vec<_>, _>>()?
        }
    };
    Ok(Json(books))
}

/// GET /books/{id}
async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = state.lock().unwrap();
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_to_book,
        )
        .map_err(|err| match err {
            rusqlite::Error::QueryReturnedNoRows => not_found(id),
            other => other.into(),
        })?;
    Ok(Json(book))
}

/// PUT /books/{id}
async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = state.lock().unwrap();
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    )?;
    if changed == 0 {
        return Err(not_found(id));
    }
    let book = Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    Ok(Json(book))
}

/// DELETE /books/{id}
async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.lock().unwrap();
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    if changed == 0 {
        return Err(not_found(id));
    }
    Ok(StatusCode::NO_CONTENT)
}

/// Map a SQLite row to a [`Book`].
fn row_to_book(row: &rusqlite::Row) -> Result<Book, rusqlite::Error> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

fn not_found(id: i64) -> ApiError {
    ApiError::new(StatusCode::NOT_FOUND, format!("book {id} not found"))
}
