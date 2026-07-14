//! A small REST API for managing a book collection.
//!
//! Storage is backed by an embedded SQLite database via `sqlx`.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use sqlx::Row;

/// A book record as stored and returned by the API.
#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Payload for creating or fully updating a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Optional filters for the list endpoint.
#[derive(Debug, Deserialize)]
pub struct ListFilter {
    pub author: Option<String>,
}

/// A JSON error body returned for non-2xx responses.
#[derive(Debug, Serialize)]
struct ApiError {
    error: String,
}

fn error_response(status: StatusCode, msg: impl Into<String>) -> Response {
    (status, Json(ApiError { error: msg.into() })).into_response()
}

/// Validate that required fields are present and non-blank.
fn validate(input: &BookInput) -> Result<(String, String), String> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();
    if title.is_empty() {
        return Err("title is required".to_string());
    }
    if author.is_empty() {
        return Err("author is required".to_string());
    }
    Ok((title, author))
}

/// Create a connection pool and ensure the schema exists.
///
/// `url` is a sqlx SQLite URL, e.g. `sqlite::memory:` or `sqlite:books.db`.
pub async fn init_pool(url: &str) -> Result<SqlitePool, sqlx::Error> {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(url)
        .await?;
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
    )
    .execute(&pool)
    .await?;
    Ok(pool)
}

/// Build the application router with the given pool as shared state.
pub fn app(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(pool)
}

async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

fn row_to_book(row: &sqlx::sqlite::SqliteRow) -> Book {
    Book {
        id: row.get("id"),
        title: row.get("title"),
        author: row.get("author"),
        year: row.get("year"),
        isbn: row.get("isbn"),
    }
}

async fn create_book(
    State(pool): State<SqlitePool>,
    Json(input): Json<BookInput>,
) -> Response {
    let (title, author) = match validate(&input) {
        Ok(v) => v,
        Err(e) => return error_response(StatusCode::BAD_REQUEST, e),
    };

    let result = sqlx::query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id",
    )
    .bind(&title)
    .bind(&author)
    .bind(input.year)
    .bind(&input.isbn)
    .fetch_one(&pool)
    .await;

    match result {
        Ok(row) => {
            let book = Book {
                id: row.get("id"),
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            (StatusCode::CREATED, Json(book)).into_response()
        }
        Err(e) => error_response(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

async fn list_books(
    State(pool): State<SqlitePool>,
    Query(filter): Query<ListFilter>,
) -> Response {
    let rows = match &filter.author {
        Some(author) => {
            sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id")
                .bind(author)
                .fetch_all(&pool)
                .await
        }
        None => {
            sqlx::query("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .fetch_all(&pool)
                .await
        }
    };

    match rows {
        Ok(rows) => {
            let books: Vec<Book> = rows.iter().map(row_to_book).collect();
            Json(books).into_response()
        }
        Err(e) => error_response(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

async fn get_book(State(pool): State<SqlitePool>, Path(id): Path<i64>) -> Response {
    let row = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&pool)
        .await;

    match row {
        Ok(Some(row)) => Json(row_to_book(&row)).into_response(),
        Ok(None) => error_response(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => error_response(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Response {
    let (title, author) = match validate(&input) {
        Ok(v) => v,
        Err(e) => return error_response(StatusCode::BAD_REQUEST, e),
    };

    let result = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&title)
    .bind(&author)
    .bind(input.year)
    .bind(&input.isbn)
    .bind(id)
    .execute(&pool)
    .await;

    match result {
        Ok(r) if r.rows_affected() == 0 => {
            error_response(StatusCode::NOT_FOUND, "book not found")
        }
        Ok(_) => {
            let book = Book {
                id,
                title,
                author,
                year: input.year,
                isbn: input.isbn,
            };
            Json(book).into_response()
        }
        Err(e) => error_response(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

async fn delete_book(State(pool): State<SqlitePool>, Path(id): Path<i64>) -> Response {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await;

    match result {
        Ok(r) if r.rows_affected() == 0 => {
            error_response(StatusCode::NOT_FOUND, "book not found")
        }
        Ok(_) => StatusCode::NO_CONTENT.into_response(),
        Err(e) => error_response(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}
