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

type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BookInput {
    title: Option<String>,
    author: Option<String>,
    year: Option<i64>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ListParams {
    author: Option<String>,
}

enum ApiError {
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

/// Opens (or creates) the SQLite database at `path` and ensures the schema exists.
/// Use ":memory:" for an in-memory database.
pub fn open_db(path: &str) -> rusqlite::Result<Connection> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
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

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

/// Validated fields of a create/update payload.
struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

fn validate(payload: Result<Json<BookInput>, JsonRejection>) -> Result<ValidBook, ApiError> {
    let Json(input) = payload.map_err(|e| ApiError::BadRequest(e.body_text()))?;
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

fn parse_id(id: &str) -> Result<i64, ApiError> {
    // A non-numeric id can never match a book.
    id.parse().map_err(|_| ApiError::NotFound)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let b = validate(payload)?;
    let conn = db.lock().unwrap();
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
    let conn = db.lock().unwrap();
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books
         WHERE ?1 IS NULL OR author = ?1 ORDER BY id",
    )?;
    let books = stmt
        .query_map(params![q.author], row_to_book)?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    Ok(Json(books))
}

async fn get_book(State(db): State<Db>, Path(id): Path<String>) -> Result<Json<Book>, ApiError> {
    let id = parse_id(&id)?;
    let conn = db.lock().unwrap();
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
    Path(id): Path<String>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(&id)?;
    let b = validate(payload)?;
    let conn = db.lock().unwrap();
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

async fn delete_book(State(db): State<Db>, Path(id): Path<String>) -> Result<StatusCode, ApiError> {
    let id = parse_id(&id)?;
    let conn = db.lock().unwrap();
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
