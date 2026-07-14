use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json},
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio_rusqlite::Connection;

#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Connection>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
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
pub struct ErrorResponse {
    pub error: String,
}

pub async fn init_db(conn: &Connection) -> Result<(), tokio_rusqlite::Error> {
    conn.call(|c| {
        c.execute(
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
    })
    .await
}

pub async fn build_app(db: Connection) -> Router {
    let state = AppState { db: Arc::new(db) };
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

fn err(status: StatusCode, msg: &str) -> (StatusCode, Json<ErrorResponse>) {
    (
        status,
        Json(ErrorResponse {
            error: msg.to_string(),
        }),
    )
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), (StatusCode, Json<ErrorResponse>)> {
    let title = input
        .title
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "title is required"))?;
    let author = input
        .author
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "author is required"))?;

    let book = Book {
        id: uuid::Uuid::new_v4().to_string(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    let b = book.clone();
    state
        .db
        .call(move |c| {
            c.execute(
                "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
                rusqlite::params![b.id, b.title, b.author, b.year, b.isbn],
            )?;
            Ok(())
        })
        .await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;

    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>, (StatusCode, Json<ErrorResponse>)> {
    let author_filter = params.get("author").cloned();
    let books = state
        .db
        .call(move |c| {
            let rows: Vec<Book> = if let Some(a) = author_filter {
                let mut stmt = c.prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")?;
                let iter = stmt.query_map([a], row_to_book)?;
                iter.collect::<Result<Vec<_>, _>>()?
            } else {
                let mut stmt = c.prepare("SELECT id, title, author, year, isbn FROM books")?;
                let iter = stmt.query_map([], row_to_book)?;
                iter.collect::<Result<Vec<_>, _>>()?
            };
            Ok(rows)
        })
        .await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
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
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let book = state
        .db
        .call(move |c| {
            let mut stmt = c.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
            let mut iter = stmt.query_map([id], row_to_book)?;
            Ok(iter.next().transpose()?)
        })
        .await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
    match book {
        Some(b) => Ok(Json(b)),
        None => Err(err(StatusCode::NOT_FOUND, "book not found")),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let title = input
        .title
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "title is required"))?;
    let author = input
        .author
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "author is required"))?;

    let book = Book {
        id: id.clone(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    let b = book.clone();
    let updated = state
        .db
        .call(move |c| {
            let n = c.execute(
                "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
                rusqlite::params![b.id, b.title, b.author, b.year, b.isbn],
            )?;
            Ok(n)
        })
        .await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
    if updated == 0 {
        return Err(err(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(Json(book))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let n = state
        .db
        .call(move |c| Ok(c.execute("DELETE FROM books WHERE id = ?1", [id])?))
        .await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()))?;
    if n == 0 {
        return Err(err(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}
