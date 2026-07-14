use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json},
    routing::{get, post},
    Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use uuid::Uuid;

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

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

fn err(status: StatusCode, msg: &str) -> (StatusCode, Json<ErrorResponse>) {
    (status, Json(ErrorResponse { error: msg.to_string() }))
}

pub fn init_db(conn: &Connection) {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )
    .expect("create table");
}

pub fn open_db(path: &str) -> Db {
    let conn = Connection::open(path).expect("open db");
    init_db(&conn);
    Arc::new(Mutex::new(conn))
}

pub fn open_memory_db() -> Db {
    let conn = Connection::open_in_memory().expect("open memory db");
    init_db(&conn);
    Arc::new(Mutex::new(conn))
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), (StatusCode, Json<ErrorResponse>)> {
    let title = input
        .title
        .as_ref()
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "title is required"))?
        .clone();
    let author = input
        .author
        .as_ref()
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "author is required"))?
        .clone();

    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };

    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )
    .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;

    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>, (StatusCode, Json<ErrorResponse>)> {
    let conn = db.lock().unwrap();
    let books = if let Some(author) = params.get("author") {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
        let rows = stmt
            .query_map(params![author], row_to_book)
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
        rows.filter_map(|r| r.ok()).collect()
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books")
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
        let rows = stmt
            .query_map([], row_to_book)
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
        rows.filter_map(|r| r.ok()).collect()
    };
    Ok(Json(books))
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

async fn get_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let conn = db.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
    let book = stmt
        .query_row(params![id], row_to_book)
        .map_err(|_| err(StatusCode::NOT_FOUND, "book not found"))?;
    Ok(Json(book))
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let title = input
        .title
        .as_ref()
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "title is required"))?
        .clone();
    let author = input
        .author
        .as_ref()
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "author is required"))?
        .clone();

    let conn = db.lock().unwrap();
    let n = conn
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, input.year, input.isbn, id],
        )
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
    if n == 0 {
        return Err(err(StatusCode::NOT_FOUND, "book not found"));
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
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let conn = db.lock().unwrap();
    let n = conn
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
    if n == 0 {
        return Err(err(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}
