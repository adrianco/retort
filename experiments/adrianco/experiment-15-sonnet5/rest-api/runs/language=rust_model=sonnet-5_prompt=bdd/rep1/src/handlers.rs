use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use rusqlite::params;
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::db::Pool;
use crate::error::AppError;
use crate::models::{Book, BookInput};

pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
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

pub async fn create_book(
    State(pool): State<Pool>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    input.validate().map_err(AppError::Validation)?;

    let conn = pool.get()?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();

    let book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )?;

    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(pool): State<Pool>,
    Query(filter): Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>, AppError> {
    let conn = pool.get()?;

    let author_filter = filter.get("author").cloned();

    let books = if let Some(author) = author_filter {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 COLLATE NOCASE ORDER BY id",
        )?;
        let rows = stmt.query_map(params![author], row_to_book)?;
        rows.collect::<Result<Vec<_>, _>>()?
    } else {
        let mut stmt =
            conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
        let rows = stmt.query_map([], row_to_book)?;
        rows.collect::<Result<Vec<_>, _>>()?
    };

    Ok(Json(books))
}

pub async fn get_book(
    State(pool): State<Pool>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let conn = pool.get()?;
    let book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )?;
    Ok(Json(book))
}

pub async fn update_book(
    State(pool): State<Pool>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, AppError> {
    input.validate().map_err(AppError::Validation)?;

    let conn = pool.get()?;
    let updated = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![input.title, input.author, input.year, input.isbn, id],
    )?;

    if updated == 0 {
        return Err(AppError::NotFound("book not found".to_string()));
    }

    let book = conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(pool): State<Pool>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let conn = pool.get()?;
    let deleted = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;

    if deleted == 0 {
        return Err(AppError::NotFound("book not found".to_string()));
    }

    Ok(StatusCode::NO_CONTENT)
}
