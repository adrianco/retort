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

pub type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize)]
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
        let (status, message) = match self {
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg),
            ApiError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            ApiError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        ApiError::Internal(err.to_string())
    }
}

fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let title = input
        .title
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| ApiError::BadRequest("title is required".to_string()))?;
    let author = input
        .author
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| ApiError::BadRequest("author is required".to_string()))?;
    Ok((title.to_string(), author.to_string()))
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

fn get_book_by_id(conn: &Connection, id: i64) -> Result<Book, ApiError> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        row_to_book,
    )
    .map_err(|err| match err {
        rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
        other => other.into(),
    })
}

async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<impl IntoResponse, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, input.year, input.isbn],
    )?;
    let book = get_book_by_id(&conn, conn.last_insert_rowid())?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(params): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().unwrap();
    let books = match params.author {
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
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().unwrap();
    Ok(Json(get_book_by_id(&conn, id)?))
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    let updated = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    )?;
    if updated == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(Json(get_book_by_id(&conn, id)?))
}

async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = db.lock().unwrap();
    let deleted = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    if deleted == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(())
}

pub fn open_db(path: &str) -> rusqlite::Result<Db> {
    let conn = if path == ":memory:" {
        Connection::open_in_memory()?
    } else {
        Connection::open(path)?
    };
    init_db(&conn)?;
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
