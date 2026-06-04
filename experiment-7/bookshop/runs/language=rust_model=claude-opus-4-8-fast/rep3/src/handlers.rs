use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use rusqlite::OptionalExtension;
use serde::Deserialize;
use serde_json::json;

use crate::db::DbPool;
use crate::models::{Book, BookInput};

/// Shared application state passed to every handler.
#[derive(Clone)]
pub struct AppState {
    pub pool: DbPool,
}

/// Map a row from the `books` table into a `Book`.
fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get("id")?,
        title: row.get("title")?,
        author: row.get("author")?,
        year: row.get("year")?,
        isbn: row.get("isbn")?,
    })
}

/// Helper to build a JSON error response with a given status code.
fn error(status: StatusCode, message: &str) -> (StatusCode, Json<serde_json::Value>) {
    (status, Json(json!({ "error": message })))
}

/// GET /health
pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// GET /books — list all books, optionally filtered by `?author=`.
pub async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<ListQuery>,
) -> impl IntoResponse {
    let conn = match state.pool.get() {
        Ok(c) => c,
        Err(e) => return error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    };

    let result = if let Some(author) = params.author.filter(|a| !a.is_empty()) {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id")
            .unwrap();
        stmt.query_map([author], row_to_book)
            .and_then(|rows| rows.collect::<rusqlite::Result<Vec<Book>>>())
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .unwrap();
        stmt.query_map([], row_to_book)
            .and_then(|rows| rows.collect::<rusqlite::Result<Vec<Book>>>())
    };

    match result {
        Ok(books) => (StatusCode::OK, Json(books)).into_response(),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    }
}

/// GET /books/{id} — fetch a single book.
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> impl IntoResponse {
    let conn = match state.pool.get() {
        Ok(c) => c,
        Err(e) => return error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    };

    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_to_book,
        )
        .optional();

    match book {
        Ok(Some(b)) => (StatusCode::OK, Json(b)).into_response(),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found").into_response(),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    }
}

/// POST /books — create a new book.
pub async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> impl IntoResponse {
    let (title, author) = match input.validate() {
        Ok(pair) => pair,
        Err(msg) => return error(StatusCode::BAD_REQUEST, &msg).into_response(),
    };

    let conn = match state.pool.get() {
        Ok(c) => c,
        Err(e) => return error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    };

    let res = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, input.year, input.isbn],
    );

    match res {
        Ok(_) => {
            let id = conn.last_insert_rowid();
            let book = Book {
                id,
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            (StatusCode::CREATED, Json(book)).into_response()
        }
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    }
}

/// PUT /books/{id} — fully update an existing book.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> impl IntoResponse {
    let (title, author) = match input.validate() {
        Ok(pair) => pair,
        Err(msg) => return error(StatusCode::BAD_REQUEST, &msg).into_response(),
    };

    let conn = match state.pool.get() {
        Ok(c) => c,
        Err(e) => return error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    };

    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, input.year, input.isbn, id],
    );

    match affected {
        Ok(0) => error(StatusCode::NOT_FOUND, "book not found").into_response(),
        Ok(_) => {
            let book = Book {
                id,
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            (StatusCode::OK, Json(book)).into_response()
        }
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    }
}

/// DELETE /books/{id} — remove a book.
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> impl IntoResponse {
    let conn = match state.pool.get() {
        Ok(c) => c,
        Err(e) => return error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    };

    let affected = conn.execute("DELETE FROM books WHERE id = ?1", [id]);

    match affected {
        Ok(0) => error(StatusCode::NOT_FOUND, "book not found").into_response(),
        Ok(_) => StatusCode::NO_CONTENT.into_response(),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()).into_response(),
    }
}
