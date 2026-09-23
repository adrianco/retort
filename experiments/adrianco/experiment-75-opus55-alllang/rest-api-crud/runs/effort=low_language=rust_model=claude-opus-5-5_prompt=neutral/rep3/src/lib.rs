use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::{Arc, Mutex};

pub type Db = Arc<Mutex<Connection>>;

#[derive(Serialize, Debug, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub enum ApiError {
    NotFound,
    Validation(Vec<String>),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        match self {
            ApiError::NotFound => {
                (StatusCode::NOT_FOUND, Json(json!({"error": "book not found"}))).into_response()
            }
            ApiError::Validation(errs) => (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": "validation failed", "details": errs})),
            )
                .into_response(),
            ApiError::Internal(e) => {
                (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))).into_response()
            }
        }
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(e.to_string())
    }
}

pub fn open_db(path: &str) -> rusqlite::Result<Db> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

/// Validates input and returns normalized (title, author).
fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let mut errs = Vec::new();
    let title = input.title.as_deref().map(str::trim).unwrap_or("");
    let author = input.author.as_deref().map(str::trim).unwrap_or("");
    if title.is_empty() {
        errs.push("title is required".to_string());
    }
    if author.is_empty() {
        errs.push("author is required".to_string());
    }
    if let Some(y) = input.year {
        if !(0..=9999).contains(&y) {
            errs.push("year must be between 0 and 9999".to_string());
        }
    }
    if errs.is_empty() {
        Ok((title.to_string(), author.to_string()))
    } else {
        Err(ApiError::Validation(errs))
    }
}

fn row_to_book(r: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: r.get(0)?,
        title: r.get(1)?,
        author: r.get(2)?,
        year: r.get(3)?,
        isbn: r.get(4)?,
    })
}

fn fetch(conn: &Connection, id: i64) -> Result<Option<Book>, ApiError> {
    Ok(conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_to_book,
        )
        .optional()?)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({"status": "ok"}))
}

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, input.year, input.isbn],
    )?;
    let book = fetch(&conn, conn.last_insert_rowid())?.ok_or(ApiError::NotFound)?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().unwrap();
    let books = match q.author {
        Some(a) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 COLLATE NOCASE ORDER BY id",
            )?;
            let rows = stmt.query_map([a], row_to_book)?;
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

async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().unwrap();
    fetch(&conn, id)?.map(Json).ok_or(ApiError::NotFound)
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    let n = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, input.year, input.isbn, id],
    )?;
    if n == 0 {
        return Err(ApiError::NotFound);
    }
    fetch(&conn, id)?.map(Json).ok_or(ApiError::NotFound)
}

async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<StatusCode, ApiError> {
    let conn = db.lock().unwrap();
    let n = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
    if n == 0 {
        Err(ApiError::NotFound)
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}
