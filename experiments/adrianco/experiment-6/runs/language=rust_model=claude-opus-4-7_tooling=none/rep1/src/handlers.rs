use crate::db;
use crate::error::{ApiError, ApiResult};
use crate::models::{Book, BookInput, ListQuery};
use crate::Db;
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

fn require_field(value: Option<&String>, name: &str) -> ApiResult<String> {
    match value {
        Some(v) if !v.trim().is_empty() => Ok(v.trim().to_string()),
        _ => Err(ApiError::Validation(format!("{name} is required"))),
    }
}

pub async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> ApiResult<(StatusCode, Json<Book>)> {
    let title = require_field(input.title.as_ref(), "title")?;
    let author = require_field(input.author.as_ref(), "author")?;
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::insert(&conn, &title, &author, input.year, input.isbn.as_deref())?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> ApiResult<Json<Vec<Book>>> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let books = db::list(&conn, q.author.as_deref())?;
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> ApiResult<Json<Book>> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::get(&conn, id)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> ApiResult<Json<Book>> {
    let title = require_field(input.title.as_ref(), "title")?;
    let author = require_field(input.author.as_ref(), "author")?;
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::update(&conn, id, &title, &author, input.year, input.isbn.as_deref())?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> ApiResult<StatusCode> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    db::delete(&conn, id)?;
    Ok(StatusCode::NO_CONTENT)
}
