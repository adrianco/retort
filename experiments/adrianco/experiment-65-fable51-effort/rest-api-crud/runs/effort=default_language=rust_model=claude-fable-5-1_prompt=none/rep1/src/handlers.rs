//! HTTP handlers for the book API.

use axum::extract::rejection::{JsonRejection, PathRejection};
use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde_json::json;

use crate::db::Db;
use crate::error::ApiError;
use crate::models::{BookInput, ListQuery};

/// `GET /health`
pub async fn health(State(db): State<Db>) -> impl IntoResponse {
    match db.ping() {
        Ok(()) => (
            StatusCode::OK,
            Json(json!({ "status": "ok", "database": "ok" })),
        ),
        Err(_) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({ "status": "degraded", "database": "unavailable" })),
        ),
    }
}

/// `POST /books`
pub async fn create_book(
    State(db): State<Db>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let Json(input) = payload?;
    let valid = input.validate().map_err(ApiError::Validation)?;
    let book = db.create(&valid)?;
    Ok((StatusCode::CREATED, Json(book)))
}

/// `GET /books?author=`
pub async fn list_books(
    State(db): State<Db>,
    Query(query): Query<ListQuery>,
) -> Result<impl IntoResponse, ApiError> {
    let author = query
        .author
        .as_deref()
        .map(str::trim)
        .filter(|a| !a.is_empty());
    let books = db.list(author)?;
    Ok(Json(books))
}

/// `GET /books/{id}`
pub async fn get_book(
    State(db): State<Db>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let Path(id) = path?;
    match db.get(id)? {
        Some(book) => Ok(Json(book)),
        None => Err(ApiError::NotFound(format!("book {id} not found"))),
    }
}

/// `PUT /books/{id}`
pub async fn update_book(
    State(db): State<Db>,
    path: Result<Path<i64>, PathRejection>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let Path(id) = path?;
    let Json(input) = payload?;
    let valid = input.validate().map_err(ApiError::Validation)?;
    match db.update(id, &valid)? {
        Some(book) => Ok(Json(book)),
        None => Err(ApiError::NotFound(format!("book {id} not found"))),
    }
}

/// `DELETE /books/{id}`
pub async fn delete_book(
    State(db): State<Db>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let Path(id) = path?;
    if db.delete(id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound(format!("book {id} not found")))
    }
}
