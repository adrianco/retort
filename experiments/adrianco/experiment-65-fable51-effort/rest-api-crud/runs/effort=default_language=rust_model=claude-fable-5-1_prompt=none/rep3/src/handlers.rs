//! HTTP request handlers.

use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;

use crate::{
    db::Db,
    error::ApiError,
    models::{Book, BookInput, ListQuery},
};

pub async fn health(State(db): State<Db>) -> impl IntoResponse {
    match db.ping() {
        Ok(()) => (
            StatusCode::OK,
            Json(json!({ "status": "ok", "database": "ok" })),
        ),
        Err(e) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({ "status": "degraded", "database": e.to_string() })),
        ),
    }
}

pub async fn create_book(
    State(db): State<Db>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let Json(input) = body?;
    let valid = input.validate().map_err(ApiError::validation)?;
    let book = db.insert(&valid)?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let author = query
        .author
        .as_deref()
        .map(str::trim)
        .filter(|a| !a.is_empty());
    let books = db.list(author)?;
    Ok(Json(books))
}

pub async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    match db.get(id)? {
        Some(book) => Ok(Json(book)),
        None => Err(ApiError::NotFound),
    }
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let Json(input) = body?;
    let valid = input.validate().map_err(ApiError::validation)?;
    match db.update(id, &valid)? {
        Some(book) => Ok(Json(book)),
        None => Err(ApiError::NotFound),
    }
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    if db.delete(id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound)
    }
}
