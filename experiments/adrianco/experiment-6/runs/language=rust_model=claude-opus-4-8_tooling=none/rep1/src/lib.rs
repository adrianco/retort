use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::json;

/// Shared application state: a SQLite connection guarded by a mutex.
pub type AppState = Arc<Mutex<Connection>>;

/// A book record as stored and returned by the API.
#[derive(Debug, Serialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Payload for creating or updating a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Query parameters for listing books.
#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// Create a connection and ensure the schema exists.
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
pub fn build_app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

/// Convenience: build an in-memory app, useful for tests.
pub fn app_in_memory() -> Router {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    init_db(&conn).expect("init schema");
    build_app(Arc::new(Mutex::new(conn)))
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get("id")?,
        title: row.get("title")?,
        author: row.get("author")?,
        year: row.get("year")?,
        isbn: row.get("isbn")?,
    })
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

/// Validate required fields, returning trimmed title/author or an error response.
fn validate(input: &BookInput) -> Result<(String, String), (StatusCode, Json<serde_json::Value>)> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();
    if title.is_empty() || author.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({ "error": "title and author are required" })),
        ));
    }
    Ok((title, author))
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> impl IntoResponse {
    let (title, author) = match validate(&input) {
        Ok(v) => v,
        Err(e) => return e.into_response(),
    };

    let conn = state.lock().unwrap();
    let result = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, input.year, input.isbn],
    );

    match result {
        Ok(_) => {
            let id = conn.last_insert_rowid();
            let book = Book {
                id,
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            (StatusCode::CREATED, Json(json!(book))).into_response()
        }
        Err(e) => internal_error(e).into_response(),
    }
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> impl IntoResponse {
    let conn = state.lock().unwrap();

    let result: rusqlite::Result<Vec<Book>> = match &q.author {
        Some(author) => {
            let mut stmt = match conn
                .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id")
            {
                Ok(s) => s,
                Err(e) => return internal_error(e).into_response(),
            };
            let rows = stmt.query_map([author], row_to_book).and_then(|m| m.collect());
            rows
        }
        None => {
            let mut stmt = match conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            {
                Ok(s) => s,
                Err(e) => return internal_error(e).into_response(),
            };
            let rows = stmt.query_map([], row_to_book).and_then(|m| m.collect());
            rows
        }
    };

    match result {
        Ok(books) => (StatusCode::OK, Json(json!(books))).into_response(),
        Err(e) => internal_error(e).into_response(),
    }
}

async fn get_book(State(state): State<AppState>, Path(id): Path<i64>) -> impl IntoResponse {
    let conn = state.lock().unwrap();
    let book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        row_to_book,
    );

    match book {
        Ok(b) => (StatusCode::OK, Json(json!(b))).into_response(),
        Err(rusqlite::Error::QueryReturnedNoRows) => not_found().into_response(),
        Err(e) => internal_error(e).into_response(),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> impl IntoResponse {
    let (title, author) = match validate(&input) {
        Ok(v) => v,
        Err(e) => return e.into_response(),
    };

    let conn = state.lock().unwrap();
    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    );

    match affected {
        Ok(0) => not_found().into_response(),
        Ok(_) => {
            let book = Book {
                id,
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            (StatusCode::OK, Json(json!(book))).into_response()
        }
        Err(e) => internal_error(e).into_response(),
    }
}

async fn delete_book(State(state): State<AppState>, Path(id): Path<i64>) -> impl IntoResponse {
    let conn = state.lock().unwrap();
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", [id]);

    match affected {
        Ok(0) => not_found().into_response(),
        Ok(_) => StatusCode::NO_CONTENT.into_response(),
        Err(e) => internal_error(e).into_response(),
    }
}

fn not_found() -> impl IntoResponse {
    (
        StatusCode::NOT_FOUND,
        Json(json!({ "error": "book not found" })),
    )
}

fn internal_error<E: std::fmt::Display>(e: E) -> impl IntoResponse {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(json!({ "error": e.to_string() })),
    )
}
