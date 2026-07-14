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

/// Shared application state: a single SQLite connection guarded by a mutex.
#[derive(Clone)]
pub struct AppState {
    pub conn: Arc<Mutex<Connection>>,
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
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// An application error that serializes to a JSON body with a status code.
pub struct AppError {
    status: StatusCode,
    message: String,
}

impl AppError {
    fn new(status: StatusCode, message: impl Into<String>) -> Self {
        Self {
            status,
            message: message.into(),
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        (self.status, Json(json!({ "error": self.message }))).into_response()
    }
}

impl From<rusqlite::Error> for AppError {
    fn from(err: rusqlite::Error) -> Self {
        AppError::new(StatusCode::INTERNAL_SERVER_ERROR, err.to_string())
    }
}

/// Initialize the database schema. Accepts any opened connection.
pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
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

/// Build the application router with the given state.
pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

/// Convenience constructor that opens an in-memory or file-backed DB and builds the app.
pub fn build_app(conn: Connection) -> Result<Router, rusqlite::Error> {
    init_db(&conn)?;
    Ok(app(AppState {
        conn: Arc::new(Mutex::new(conn)),
    }))
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

/// Validate and normalize required string fields.
fn require(field: &str, value: &Option<String>) -> Result<String, AppError> {
    match value {
        Some(v) if !v.trim().is_empty() => Ok(v.trim().to_string()),
        _ => Err(AppError::new(
            StatusCode::BAD_REQUEST,
            format!("{field} is required"),
        )),
    }
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<Response, AppError> {
    let title = require("title", &input.title)?;
    let author = require("author", &input.author)?;

    let conn = state.conn.lock().unwrap();
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
    Ok((StatusCode::CREATED, Json(book)).into_response())
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let conn = state.conn.lock().unwrap();
    let books = match q.author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map([author], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()?
        }
    };
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let conn = state.conn.lock().unwrap();
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                AppError::new(StatusCode::NOT_FOUND, "book not found")
            }
            other => other.into(),
        })?;
    Ok(Json(book))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, AppError> {
    let title = require("title", &input.title)?;
    let author = require("author", &input.author)?;

    let conn = state.conn.lock().unwrap();
    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    )?;
    if affected == 0 {
        return Err(AppError::new(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(Json(Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    }))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let conn = state.conn.lock().unwrap();
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    if affected == 0 {
        return Err(AppError::new(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
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
