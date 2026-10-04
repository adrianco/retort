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
use rusqlite::{params, Connection, OptionalExtension, Row};
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Clone)]
pub struct AppState {
    db: Arc<Mutex<Connection>>,
}

impl AppState {
    /// Opens (creating if needed) the SQLite database at `path` and ensures the schema exists.
    /// Use `":memory:"` for an ephemeral database.
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
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
        Ok(Self {
            db: Arc::new(Mutex::new(conn)),
        })
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

impl Book {
    fn from_row(row: &Row) -> rusqlite::Result<Self> {
        Ok(Self {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    }
}

/// Request body for create and update. Fields are optional here so that missing
/// required fields produce a descriptive validation error rather than a parse error.
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

impl BookInput {
    fn validate(self) -> Result<ValidBook, ApiError> {
        let title = self.title.map(|s| s.trim().to_string()).unwrap_or_default();
        let author = self.author.map(|s| s.trim().to_string()).unwrap_or_default();
        let mut errors = Vec::new();
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
    Validation(Vec<String>),
    BadRequest(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::Validation(details) => (
                StatusCode::BAD_REQUEST,
                json!({ "error": "validation failed", "details": details }),
            ),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": msg })),
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
        ApiError::BadRequest(format!("invalid JSON body: {}", e.body_text()))
    }
}

impl From<PathRejection> for ApiError {
    fn from(_: PathRejection) -> Self {
        ApiError::BadRequest("book id must be an integer".to_string())
    }
}

type ApiResult<T> = Result<T, ApiError>;
type IdPath = Result<Path<i64>, PathRejection>;
type Body = Result<Json<BookInput>, JsonRejection>;

const SELECT: &str = "SELECT id, title, author, year, isbn FROM books";

pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .fallback(|| async { (StatusCode::NOT_FOUND, Json(json!({ "error": "not found" }))) })
        .with_state(state)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

#[derive(Deserialize)]
struct ListParams {
    author: Option<String>,
}

async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<ListParams>,
) -> ApiResult<Json<Vec<Book>>> {
    let db = state.db.lock().unwrap();
    let books = match params.author {
        Some(author) => db
            .prepare(&format!("{SELECT} WHERE author = ?1 COLLATE NOCASE ORDER BY id"))?
            .query_map(params![author], Book::from_row)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
        None => db
            .prepare(&format!("{SELECT} ORDER BY id"))?
            .query_map([], Book::from_row)?
            .collect::<rusqlite::Result<Vec<_>>>()?,
    };
    Ok(Json(books))
}

fn fetch(db: &Connection, id: i64) -> ApiResult<Book> {
    db.query_row(&format!("{SELECT} WHERE id = ?1"), params![id], Book::from_row)
        .optional()?
        .ok_or(ApiError::NotFound)
}

async fn create_book(State(state): State<AppState>, body: Body) -> ApiResult<Response> {
    let Json(input) = body?;
    let book = input.validate()?;
    let db = state.db.lock().unwrap();
    db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![book.title, book.author, book.year, book.isbn],
    )?;
    let created = fetch(&db, db.last_insert_rowid())?;
    let location = format!("/books/{}", created.id);
    Ok((
        StatusCode::CREATED,
        [(axum::http::header::LOCATION, location)],
        Json(created),
    )
        .into_response())
}

async fn get_book(State(state): State<AppState>, id: IdPath) -> ApiResult<Json<Book>> {
    let Path(id) = id?;
    let db = state.db.lock().unwrap();
    Ok(Json(fetch(&db, id)?))
}

async fn update_book(
    State(state): State<AppState>,
    id: IdPath,
    body: Body,
) -> ApiResult<Json<Book>> {
    let Path(id) = id?;
    let Json(input) = body?;
    let book = input.validate()?;
    let db = state.db.lock().unwrap();
    let changed = db.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(fetch(&db, id)?))
}

async fn delete_book(State(state): State<AppState>, id: IdPath) -> ApiResult<StatusCode> {
    let Path(id) = id?;
    let db = state.db.lock().unwrap();
    let changed = db.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
