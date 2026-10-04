use std::sync::{Arc, Mutex};

use axum::{
    extract::{rejection::JsonRejection, rejection::PathRejection, Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension, Row};
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
    BadRequest(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(json!({ "error": msg }))).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(e.to_string())
    }
}

/// Opens (and initializes) the SQLite database. Use ":memory:" for an in-memory DB.
pub fn open_db(path: &str) -> rusqlite::Result<Connection> {
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

fn row_to_book(row: &Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

fn fetch_book(conn: &Connection, id: i64) -> Result<Book, ApiError> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()?
    .ok_or(ApiError::NotFound)
}

/// Validated fields of a book payload: (title, author, year, isbn).
fn validate(
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<(String, String, Option<i64>, Option<String>), ApiError> {
    let Json(input) = payload.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    let title = input.title.map(|t| t.trim().to_string()).unwrap_or_default();
    let author = input.author.map(|a| a.trim().to_string()).unwrap_or_default();
    if title.is_empty() {
        return Err(ApiError::BadRequest("title is required".into()));
    }
    if author.is_empty() {
        return Err(ApiError::BadRequest("author is required".into()));
    }
    Ok((title, author, input.year, input.isbn))
}

fn parse_id(path: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    path.map(|Path(id)| id)
        .map_err(|_| ApiError::BadRequest("invalid book id".into()))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author, year, isbn) = validate(payload)?;
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, year, isbn],
    )?;
    let book = fetch_book(&conn, conn.last_insert_rowid())?;
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

async fn get_book(
    State(db): State<Db>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(path)?;
    let conn = db.lock().unwrap();
    Ok(Json(fetch_book(&conn, id)?))
}

async fn update_book(
    State(db): State<Db>,
    path: Result<Path<i64>, PathRejection>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(path)?;
    let (title, author, year, isbn) = validate(payload)?;
    let conn = db.lock().unwrap();
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(fetch_book(&conn, id)?))
}

async fn delete_book(
    State(db): State<Db>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let id = parse_id(path)?;
    let conn = db.lock().unwrap();
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
