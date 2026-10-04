use std::sync::{Arc, Mutex};

use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::json;

pub type Db = Arc<Mutex<Connection>>;

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
        let (status, body) = match self {
            ApiError::Validation(details) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                json!({"error": "validation failed", "details": details}),
            ),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({"error": msg})),
            ApiError::NotFound => (StatusCode::NOT_FOUND, json!({"error": "book not found"})),
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    json!({"error": "internal server error"}),
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

/// Opens (or creates) the SQLite database at `path` and ensures the schema exists.
/// Use ":memory:" for an in-memory database.
pub fn open_db(path: &str) -> rusqlite::Result<Db> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )?;
    Ok(Arc::new(Mutex::new(conn)))
}

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

/// Validated, trimmed title and author.
fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let mut errors = Vec::new();
    let title = input.title.as_deref().map(str::trim).unwrap_or("");
    let author = input.author.as_deref().map(str::trim).unwrap_or("");
    if title.is_empty() {
        errors.push("title is required".to_string());
    }
    if author.is_empty() {
        errors.push("author is required".to_string());
    }
    if errors.is_empty() {
        Ok((title.to_string(), author.to_string()))
    } else {
        Err(ApiError::Validation(errors))
    }
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
    db.lock().map_err(|e| ApiError::Internal(e.to_string()))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({"status": "ok"}))
}

async fn create_book(
    State(db): State<Db>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let Json(input) = payload?;
    let (title, author) = validate(&input)?;
    let conn = lock(&db)?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, input.year, input.isbn],
    )?;
    let book = Book {
        id: conn.last_insert_rowid(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = lock(&db)?;
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books
         WHERE ?1 IS NULL OR author = ?1 ORDER BY id",
    )?;
    let books = stmt
        .query_map(params![q.author], row_to_book)?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    Ok(Json(books))
}

async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    let conn = lock(&db)?;
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()?
    .map(Json)
    .ok_or(ApiError::NotFound)
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let Json(input) = payload?;
    let (title, author) = validate(&input)?;
    let conn = lock(&db)?;
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, input.year, input.isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    }))
}

async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<StatusCode, ApiError> {
    let conn = lock(&db)?;
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
