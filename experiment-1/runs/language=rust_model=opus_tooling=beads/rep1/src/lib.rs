use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
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
struct ErrorBody {
    error: String,
}

fn err(status: StatusCode, msg: &str) -> Response {
    (status, Json(ErrorBody { error: msg.into() })).into_response()
}

pub fn init_db(path: &str) -> rusqlite::Result<Connection> {
    let conn = if path == ":memory:" {
        Connection::open_in_memory()?
    } else {
        Connection::open(path)?
    };
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
    Ok(conn)
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

async fn health() -> Response {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"}))).into_response()
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

async fn list_books(
    State(db): State<Db>,
    Query(params): Query<HashMap<String, String>>,
) -> Response {
    let conn = db.lock().unwrap();
    let result: rusqlite::Result<Vec<Book>> = if let Some(author) = params.get("author") {
        let mut stmt = match conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")
        {
            Ok(s) => s,
            Err(e) => return err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
        };
        stmt.query_map(params![author], row_to_book)
            .and_then(|rows| rows.collect())
    } else {
        let mut stmt = match conn.prepare("SELECT id, title, author, year, isbn FROM books") {
            Ok(s) => s,
            Err(e) => return err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
        };
        stmt.query_map([], row_to_book).and_then(|rows| rows.collect())
    };
    match result {
        Ok(books) => (StatusCode::OK, Json(books)).into_response(),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

async fn create_book(State(db): State<Db>, Json(input): Json<BookInput>) -> Response {
    let title = match input.title.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
        Some(t) => t.to_string(),
        None => return err(StatusCode::BAD_REQUEST, "title is required"),
    };
    let author = match input.author.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
        Some(a) => a.to_string(),
        None => return err(StatusCode::BAD_REQUEST, "author is required"),
    };
    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    let conn = db.lock().unwrap();
    if let Err(e) = conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    ) {
        return err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string());
    }
    (StatusCode::CREATED, Json(book)).into_response()
}

async fn get_book(State(db): State<Db>, Path(id): Path<String>) -> Response {
    let conn = db.lock().unwrap();
    let result = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    );
    match result {
        Ok(book) => (StatusCode::OK, Json(book)).into_response(),
        Err(rusqlite::Error::QueryReturnedNoRows) => err(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Response {
    let title = match input.title.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
        Some(t) => t.to_string(),
        None => return err(StatusCode::BAD_REQUEST, "title is required"),
    };
    let author = match input.author.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
        Some(a) => a.to_string(),
        None => return err(StatusCode::BAD_REQUEST, "author is required"),
    };
    let conn = db.lock().unwrap();
    let changed = match conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, input.year, input.isbn, id],
    ) {
        Ok(n) => n,
        Err(e) => return err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    };
    if changed == 0 {
        return err(StatusCode::NOT_FOUND, "book not found");
    }
    let book = Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    (StatusCode::OK, Json(book)).into_response()
}

async fn delete_book(State(db): State<Db>, Path(id): Path<String>) -> Response {
    let conn = db.lock().unwrap();
    let changed = match conn.execute("DELETE FROM books WHERE id = ?1", params![id]) {
        Ok(n) => n,
        Err(e) => return err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    };
    if changed == 0 {
        return err(StatusCode::NOT_FOUND, "book not found");
    }
    StatusCode::NO_CONTENT.into_response()
}
