use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json},
};
use serde::Deserialize;
use std::sync::Arc;
use uuid::Uuid;

use crate::db::Db;
use crate::models::{Book, BookInput, ErrorResponse};

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

fn validate(input: &BookInput) -> Result<(String, String), String> {
    let title = input
        .title
        .as_ref()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| "title is required".to_string())?;
    let author = input
        .author
        .as_ref()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| "author is required".to_string())?;
    Ok((title, author))
}

fn err(status: StatusCode, msg: impl Into<String>) -> (StatusCode, Json<ErrorResponse>) {
    (status, Json(ErrorResponse { error: msg.into() }))
}

pub async fn create_book(
    State(db): State<Arc<Db>>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), (StatusCode, Json<ErrorResponse>)> {
    let (title, author) =
        validate(&input).map_err(|m| err(StatusCode::BAD_REQUEST, m))?;
    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    db.insert(&book)
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Arc<Db>>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, (StatusCode, Json<ErrorResponse>)> {
    let books = db
        .list(q.author.as_deref())
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Arc<Db>>,
    Path(id): Path<String>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    match db
        .get(&id)
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
    {
        Some(b) => Ok(Json(b)),
        None => Err(err(StatusCode::NOT_FOUND, "book not found")),
    }
}

pub async fn update_book(
    State(db): State<Arc<Db>>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let (title, author) =
        validate(&input).map_err(|m| err(StatusCode::BAD_REQUEST, m))?;
    let existing = db
        .get(&id)
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
        .ok_or_else(|| err(StatusCode::NOT_FOUND, "book not found"))?;
    let updated = Book {
        id: existing.id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };
    db.update(&updated)
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(updated))
}

pub async fn delete_book(
    State(db): State<Arc<Db>>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let n = db
        .delete(&id)
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    if n == 0 {
        Err(err(StatusCode::NOT_FOUND, "book not found"))
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}
