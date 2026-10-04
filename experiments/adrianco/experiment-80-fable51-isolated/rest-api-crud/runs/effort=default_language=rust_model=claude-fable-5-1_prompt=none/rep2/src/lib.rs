//! REST API for managing a book collection, backed by SQLite.

use std::sync::{Arc, Mutex, MutexGuard};

use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension, Row};
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Clone)]
pub struct AppState {
    db: Arc<Mutex<Connection>>,
}

impl AppState {
    fn conn(&self) -> MutexGuard<'_, Connection> {
        // A poisoned lock only means another request panicked; the connection is still usable.
        self.db.lock().unwrap_or_else(|e| e.into_inner())
    }
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    title: Option<String>,
    author: Option<String>,
    year: Option<i64>,
    isbn: Option<String>,
}

/// A validated `BookInput`: title and author are present and non-blank.
struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListParams {
    author: Option<String>,
}

#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),
    Validation(Vec<String>),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": msg })),
            ApiError::Validation(details) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                json!({ "error": "validation failed", "details": details }),
            ),
            ApiError::NotFound => (StatusCode::NOT_FOUND, json!({ "error": "book not found" })),
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    json!({ "error": "internal server error" }),
                )
            }
        };
        (status, Json(body)).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(e.to_string())
    }
}

impl From<JsonRejection> for ApiError {
    fn from(e: JsonRejection) -> Self {
        ApiError::BadRequest(e.body_text())
    }
}

fn validate(input: BookInput) -> Result<ValidBook, ApiError> {
    let mut errors = Vec::new();
    let title = input.title.map(|t| t.trim().to_string()).unwrap_or_default();
    let author = input.author.map(|a| a.trim().to_string()).unwrap_or_default();
    if title.is_empty() {
        errors.push("title is required".to_string());
    }
    if author.is_empty() {
        errors.push("author is required".to_string());
    }
    if !errors.is_empty() {
        return Err(ApiError::Validation(errors));
    }
    Ok(ValidBook {
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    })
}

fn row_to_book(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

fn find_book(conn: &Connection, id: i64) -> Result<Book, ApiError> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()?
    .ok_or(ApiError::NotFound)
}

/// Creates the schema if it does not exist yet.
pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);",
    )
}

/// Builds the application router on top of an open SQLite connection.
pub fn app(conn: Connection) -> rusqlite::Result<Router> {
    init_db(&conn)?;
    let state = AppState {
        db: Arc::new(Mutex::new(conn)),
    };
    Ok(Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(state): State<AppState>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let Json(input) = payload?;
    let book = validate(input)?;
    let conn = state.conn();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![book.title, book.author, book.year, book.isbn],
    )?;
    let created = find_book(&conn, conn.last_insert_rowid())?;
    Ok((StatusCode::CREATED, Json(created)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.conn();
    let books = match query.author {
        Some(author) => conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id")?
            .query_map(params![author], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
        None => conn
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?
            .query_map([], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
    };
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    Ok(Json(find_book(&state.conn(), id)?))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let Json(input) = payload?;
    let book = validate(input)?;
    let conn = state.conn();
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(find_book(&conn, id)?))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let changed = state
        .conn()
        .execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
