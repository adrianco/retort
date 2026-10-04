//! REST API for managing a book collection, backed by SQLite.

use std::sync::{Arc, Mutex};

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

type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Request body for create/update. Fields are optional so that missing
/// required fields produce a validation error rather than a parse error.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub author: Option<String>,
}

pub enum ApiError {
    Validation(Vec<String>),
    BadRequest(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        match self {
            ApiError::Validation(details) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!({ "error": "validation failed", "details": details })),
            ),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, Json(json!({ "error": msg }))),
            ApiError::NotFound => (
                StatusCode::NOT_FOUND,
                Json(json!({ "error": "book not found" })),
            ),
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({ "error": "internal server error" })),
                )
            }
        }
        .into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(e.to_string())
    }
}

impl From<JsonRejection> for ApiError {
    fn from(e: JsonRejection) -> Self {
        ApiError::BadRequest(format!("invalid JSON body: {}", e.body_text()))
    }
}

impl From<PathRejection> for ApiError {
    fn from(_: PathRejection) -> Self {
        ApiError::BadRequest("book id must be an integer".to_string())
    }
}

/// Opens (and initialises) the database. Use `":memory:"` for an in-memory DB.
pub fn open_db(path: &str) -> rusqlite::Result<Connection> {
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
    Ok(conn)
}

pub fn app(conn: Connection) -> Router {
    let db: Db = Arc::new(Mutex::new(conn));
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

/// Validated, trimmed book fields.
struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
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
    Ok(ValidBook {
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    })
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

fn lock(db: &Db) -> Result<std::sync::MutexGuard<'_, Connection>, ApiError> {
    db.lock()
        .map_err(|_| ApiError::Internal("database lock poisoned".to_string()))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let Json(input) = body?;
    let b = validate(input)?;
    let conn = lock(&db)?;
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

async fn list_books(
    State(db): State<Db>,
    Query(params): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = lock(&db)?;
    let books = match params.author {
        Some(author) => conn
            .prepare(
                "SELECT id, title, author, year, isbn FROM books \
                 WHERE author = ?1 COLLATE NOCASE ORDER BY id",
            )?
            .query_map([author], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
        None => conn
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?
            .query_map([], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
    };
    Ok(Json(books))
}

async fn get_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let Path(id) = id?;
    let conn = lock(&db)?;
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        row_to_book,
    )
    .optional()?
    .map(Json)
    .ok_or(ApiError::NotFound)
}

async fn update_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let Path(id) = id?;
    let Json(input) = body?;
    let b = validate(input)?;
    let conn = lock(&db)?;
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![b.title, b.author, b.year, b.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(Book {
        id,
        title: b.title,
        author: b.author,
        year: b.year,
        isbn: b.isbn,
    }))
}

async fn delete_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let Path(id) = id?;
    let conn = lock(&db)?;
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
