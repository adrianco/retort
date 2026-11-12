//! Book collection REST API backed by SQLite.

use std::sync::{Arc, Mutex, MutexGuard};

use axum::{
    extract::{
        rejection::{JsonRejection, PathRejection},
        Path, Query, State,
    },
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Clone)]
pub struct Db(Arc<Mutex<Connection>>);

impl Db {
    /// Open (and migrate) a database file; use ":memory:" for an in-memory DB.
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            );",
        )?;
        Ok(Db(Arc::new(Mutex::new(conn))))
    }

    fn conn(&self) -> MutexGuard<'_, Connection> {
        self.0.lock().unwrap_or_else(|e| e.into_inner())
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

struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

pub enum ApiError {
    NotFound,
    BadRequest(StatusCode, String),
    Validation(Vec<String>),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        match self {
            ApiError::NotFound => {
                (StatusCode::NOT_FOUND, Json(json!({"error": "book not found"}))).into_response()
            }
            ApiError::BadRequest(status, msg) => (status, Json(json!({"error": msg}))).into_response(),
            ApiError::Validation(details) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!({"error": "validation failed", "details": details})),
            )
                .into_response(),
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({"error": "internal server error"})),
                )
                    .into_response()
            }
        }
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(e.to_string())
    }
}

impl From<JsonRejection> for ApiError {
    fn from(e: JsonRejection) -> Self {
        ApiError::BadRequest(e.status(), e.body_text())
    }
}

impl From<PathRejection> for ApiError {
    fn from(_: PathRejection) -> Self {
        ApiError::BadRequest(StatusCode::BAD_REQUEST, "invalid book id".into())
    }
}

fn validate(input: BookInput) -> Result<ValidBook, ApiError> {
    let mut errors = Vec::new();
    let title = input.title.unwrap_or_default().trim().to_string();
    let author = input.author.unwrap_or_default().trim().to_string();
    if title.is_empty() {
        errors.push("title is required".to_string());
    }
    if author.is_empty() {
        errors.push("author is required".to_string());
    }
    if !errors.is_empty() {
        return Err(ApiError::Validation(errors));
    }
    Ok(ValidBook { title, author, year: input.year, isbn: input.isbn })
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

const SELECT: &str = "SELECT id, title, author, year, isbn FROM books";

type ApiResult<T> = Result<T, ApiError>;

async fn health() -> Json<serde_json::Value> {
    Json(json!({"status": "ok"}))
}

async fn create_book(
    State(db): State<Db>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> ApiResult<(StatusCode, Json<Book>)> {
    let b = validate(body?.0)?;
    let conn = db.conn();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![b.title, b.author, b.year, b.isbn],
    )?;
    let book = Book {
        id: conn.last_insert_rowid(),
        title: b.title,
        author: b.author,
        year: b.year,
        isbn: b.isbn,
    };
    Ok((StatusCode::CREATED, Json(book)))
}

#[derive(Deserialize)]
struct ListParams {
    author: Option<String>,
}

async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListParams>,
) -> ApiResult<Json<Vec<Book>>> {
    let conn = db.conn();
    let books = match q.author {
        Some(author) => conn
            .prepare(&format!("{SELECT} WHERE author = ?1 COLLATE NOCASE ORDER BY id"))?
            .query_map(params![author], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
        None => conn
            .prepare(&format!("{SELECT} ORDER BY id"))?
            .query_map([], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
    };
    Ok(Json(books))
}

async fn get_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> ApiResult<Json<Book>> {
    let id = id?.0;
    db.conn()
        .query_row(&format!("{SELECT} WHERE id = ?1"), params![id], row_to_book)
        .optional()?
        .map(Json)
        .ok_or(ApiError::NotFound)
}

async fn update_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> ApiResult<Json<Book>> {
    let id = id?.0;
    let b = validate(body?.0)?;
    let changed = db.conn().execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![b.title, b.author, b.year, b.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(Book { id, title: b.title, author: b.author, year: b.year, isbn: b.isbn }))
}

async fn delete_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> ApiResult<StatusCode> {
    let id = id?.0;
    let changed = db.conn().execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

/// Build the application router.
pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}
