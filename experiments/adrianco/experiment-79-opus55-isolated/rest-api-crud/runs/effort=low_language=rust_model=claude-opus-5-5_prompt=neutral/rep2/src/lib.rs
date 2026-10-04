//! REST API for managing a book collection, backed by SQLite.

use std::sync::{Arc, Mutex};

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

#[derive(Debug, Serialize, Deserialize, PartialEq)]
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

struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

impl BookInput {
    fn validate(self) -> Result<ValidBook, ApiError> {
        let mut errors = Vec::new();
        let title = self.title.unwrap_or_default().trim().to_string();
        let author = self.author.unwrap_or_default().trim().to_string();
        if title.is_empty() {
            errors.push("title is required".to_string());
        }
        if author.is_empty() {
            errors.push("author is required".to_string());
        }
        if !errors.is_empty() {
            return Err(ApiError::Validation(errors));
        }
        let isbn = self
            .isbn
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        Ok(ValidBook {
            title,
            author,
            year: self.year,
            isbn,
        })
    }
}

#[derive(Debug)]
pub enum ApiError {
    NotFound,
    BadRequest(String),
    Validation(Vec<String>),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::NotFound => (StatusCode::NOT_FOUND, json!({ "error": "book not found" })),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": msg })),
            ApiError::Validation(details) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                json!({ "error": "validation failed", "details": details }),
            ),
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

/// Shared handle to the SQLite database.
#[derive(Clone)]
pub struct Db(Arc<Mutex<Connection>>);

impl Db {
    /// Opens (creating if needed) a database file and ensures the schema exists.
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        Self::init(Connection::open(path)?)
    }

    pub fn in_memory() -> rusqlite::Result<Self> {
        Self::init(Connection::open_in_memory()?)
    }

    fn init(conn: Connection) -> rusqlite::Result<Self> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);",
        )?;
        Ok(Db(Arc::new(Mutex::new(conn))))
    }

    fn conn(&self) -> std::sync::MutexGuard<'_, Connection> {
        // A poisoned lock only means another request panicked; the connection is still usable.
        self.0.lock().unwrap_or_else(|e| e.into_inner())
    }
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

const SELECT: &str = "SELECT id, title, author, year, isbn FROM books";

fn parse_id(raw: &str) -> Result<i64, ApiError> {
    raw.parse().map_err(|_| ApiError::NotFound)
}

fn parse_body(body: Result<Json<BookInput>, JsonRejection>) -> Result<ValidBook, ApiError> {
    let Json(input) = body.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    input.validate()
}

#[derive(Debug, Deserialize)]
struct ListParams {
    author: Option<String>,
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let b = parse_body(body)?;
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

async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.conn();
    let books = match q.author {
        Some(author) => conn
            .prepare(&format!(
                "{SELECT} WHERE author = ?1 COLLATE NOCASE ORDER BY id"
            ))?
            .query_map(params![author], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
        None => conn
            .prepare(&format!("{SELECT} ORDER BY id"))?
            .query_map([], row_to_book)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
    };
    Ok(Json(books))
}

async fn get_book(State(db): State<Db>, Path(id): Path<String>) -> Result<Json<Book>, ApiError> {
    let id = parse_id(&id)?;
    db.conn()
        .query_row(&format!("{SELECT} WHERE id = ?1"), params![id], row_to_book)
        .optional()?
        .map(Json)
        .ok_or(ApiError::NotFound)
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(&id)?;
    let b = parse_body(body)?;
    let changed = db.conn().execute(
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
    Path(id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let id = parse_id(&id)?;
    let changed = db
        .conn()
        .execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

/// Builds the application router.
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
