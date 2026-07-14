use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde_json::json;

use crate::error::AppError;
use crate::models::{Book, BookInput, BookQuery};

pub type SharedDb = Arc<Mutex<Connection>>;

pub async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

pub async fn create_book(
    State(db): State<SharedDb>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let (title, author) = input.validate().map_err(AppError::Validation)?;

    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();

    let book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        Book::from_row,
    )?;

    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<SharedDb>,
    Query(query): Query<BookQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let conn = db.lock().unwrap();

    let books = match query.author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map(params![author], Book::from_row)?;
            rows.collect::<rusqlite::Result<Vec<Book>>>()?
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], Book::from_row)?;
            rows.collect::<rusqlite::Result<Vec<Book>>>()?
        }
    };

    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<SharedDb>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let conn = db.lock().unwrap();
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            Book::from_row,
        )
        .optional()?
        .ok_or(AppError::NotFound)?;

    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<SharedDb>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, AppError> {
    let (title, author) = input.validate().map_err(AppError::Validation)?;

    let conn = db.lock().unwrap();
    let updated = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, input.year, input.isbn, id],
    )?;

    if updated == 0 {
        return Err(AppError::NotFound);
    }

    let book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        Book::from_row,
    )?;

    Ok(Json(book))
}

pub async fn delete_book(
    State(db): State<SharedDb>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let conn = db.lock().unwrap();
    let deleted = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;

    if deleted == 0 {
        return Err(AppError::NotFound);
    }

    Ok(StatusCode::NO_CONTENT)
}
