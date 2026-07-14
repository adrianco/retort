use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

pub type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

pub enum ApiError {
    NotFound,
    BadRequest(String),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            ApiError::NotFound => (StatusCode::NOT_FOUND, "not found".to_string()),
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(ErrorResponse { error: msg })).into_response()
    }
}

pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
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
    let conn = Connection::open(path)?;
    init_db(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn open_memory_db() -> rusqlite::Result<Db> {
    let conn = Connection::open_in_memory()?;
    init_db(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
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

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let title = input.title.unwrap_or_default();
    let author = input.author.unwrap_or_default();
    if title.trim().is_empty() {
        return Err(ApiError::BadRequest("title is required".to_string()));
    }
    if author.trim().is_empty() {
        return Err(ApiError::BadRequest("author is required".to_string()));
    }
    let book = Book {
        id: uuid::Uuid::new_v4().to_string(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )
    .map_err(|e| ApiError::Internal(e.to_string()))?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let books: Vec<Book> = if let Some(author) = q.author {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        let rows = stmt
            .query_map(params![author], row_to_book)
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        rows.filter_map(|r| r.ok()).collect()
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books")
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        let rows = stmt
            .query_map([], row_to_book)
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        rows.filter_map(|r| r.ok()).collect()
    };
    Ok(Json(books))
}

async fn get_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
            other => ApiError::Internal(other.to_string()),
        })?;
    Ok(Json(book))
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let title = input.title.unwrap_or_default();
    let author = input.author.unwrap_or_default();
    if title.trim().is_empty() {
        return Err(ApiError::BadRequest("title is required".to_string()));
    }
    if author.trim().is_empty() {
        return Err(ApiError::BadRequest("author is required".to_string()));
    }
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let n = conn
        .execute(
            "UPDATE books SET title=?1, author=?2, year=?3, isbn=?4 WHERE id=?5",
            params![title, author, input.year, input.isbn, id],
        )
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if n == 0 {
        return Err(ApiError::NotFound);
    }
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    Ok(Json(book))
}

async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let n = conn
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if n == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
