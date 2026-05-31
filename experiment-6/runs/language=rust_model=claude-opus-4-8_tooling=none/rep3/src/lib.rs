//! Book collection REST API.
//!
//! Exposes a small CRUD API backed by SQLite. The router is constructed by
//! [`app`] from a shared connection so it can be exercised directly in tests
//! without binding a TCP socket.

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::json;

/// Shared application state: a single SQLite connection guarded by a mutex.
pub type Db = Arc<Mutex<Connection>>;

/// A book record as stored and returned by the API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Request body for creating or updating a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Filter parameters for listing books.
#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub author: Option<String>,
}

/// An API error carrying an HTTP status and a human-readable message.
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
        ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, err.to_string())
    }
}

/// Open a connection at `path` (use `":memory:"` for an in-memory database) and
/// ensure the schema exists.
pub fn open_db(path: &str) -> rusqlite::Result<Connection> {
    let conn = Connection::open(path)?;
    init_schema(&conn)?;
    Ok(conn)
}

/// Create the `books` table if it does not already exist.
pub fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
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
    Ok(())
}

/// Build the application router from a shared database connection.
pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

/// Validate and normalise the required string fields, trimming whitespace.
fn require_fields(input: &BookInput) -> Result<(String, String), ApiError> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();

    if title.is_empty() {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            "title is required",
        ));
    }
    if author.is_empty() {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            "author is required",
        ));
    }
    Ok((title, author))
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

/// `GET /health` — liveness probe.
async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

/// `POST /books` — create a new book.
async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<impl IntoResponse, ApiError> {
    let (title, author) = require_fields(&input)?;

    let conn = db.lock().unwrap();
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

/// `GET /books` — list all books, optionally filtered by `?author=`.
async fn list_books(
    State(db): State<Db>,
    Query(params): Query<ListParams>,
) -> Result<impl IntoResponse, ApiError> {
    let conn = db.lock().unwrap();
    let books = match params.author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books \
                 WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map([author], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
        None => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
    };
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch a single book.
async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<impl IntoResponse, ApiError> {
    let conn = db.lock().unwrap();
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                ApiError::new(StatusCode::NOT_FOUND, "book not found")
            }
            other => other.into(),
        })?;
    Ok(Json(book))
}

/// `PUT /books/{id}` — replace an existing book.
async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<impl IntoResponse, ApiError> {
    let (title, author) = require_fields(&input)?;

    let conn = db.lock().unwrap();
    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    )?;

    if affected == 0 {
        return Err(ApiError::new(StatusCode::NOT_FOUND, "book not found"));
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

/// `DELETE /books/{id}` — remove a book.
async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<impl IntoResponse, ApiError> {
    let conn = db.lock().unwrap();
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    if affected == 0 {
        return Err(ApiError::new(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}
