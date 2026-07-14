use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::Json;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::db::{self, Db};
use crate::error::AppError;
use crate::models::{Book, CreateBook, ListQuery, UpdateBook};

pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

pub async fn create_book(
    State(db): State<Db>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let title = required(payload.title, "title")?;
    let author = required(payload.author, "author")?;
    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: payload.year,
        isbn: payload.isbn,
    };
    db::insert(&db, &book)?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = db::list(&db, q.author.as_deref())?;
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<Json<Book>, AppError> {
    match db::get(&db, &id)? {
        Some(b) => Ok(Json(b)),
        None => Err(AppError::NotFound),
    }
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    let existing = db::get(&db, &id)?.ok_or(AppError::NotFound)?;
    let title = payload.title.unwrap_or(existing.title);
    let author = payload.author.unwrap_or(existing.author);
    if title.trim().is_empty() {
        return Err(AppError::Validation("title must not be empty".into()));
    }
    if author.trim().is_empty() {
        return Err(AppError::Validation("author must not be empty".into()));
    }
    let updated = Book {
        id: existing.id,
        title,
        author,
        year: payload.year.or(existing.year),
        isbn: payload.isbn.or(existing.isbn),
    };
    if !db::update(&db, &updated)? {
        return Err(AppError::NotFound);
    }
    Ok(Json(updated))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<StatusCode, AppError> {
    if db::delete(&db, &id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(AppError::NotFound)
    }
}

fn required(value: Option<String>, field: &str) -> Result<String, AppError> {
    match value {
        Some(s) if !s.trim().is_empty() => Ok(s),
        _ => Err(AppError::Validation(format!("{field} is required"))),
    }
}
