//! HTTP handlers for the books API.

use axum::{
    extract::{
        rejection::{JsonRejection, PathRejection},
        Path, Query, State,
    },
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;

use crate::{
    db,
    error::ApiError,
    models::{Book, BookInput, ListQuery},
    AppState,
};

type JsonBody = Result<Json<BookInput>, JsonRejection>;
type IdPath = Result<Path<i64>, PathRejection>;

/// `GET /health` — liveness check that also verifies the database responds.
pub async fn health(State(state): State<AppState>) -> Result<Json<serde_json::Value>, ApiError> {
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    conn.query_row("SELECT 1", [], |_| Ok(()))?;
    Ok(Json(json!({ "status": "ok" })))
}

/// `POST /books` — create a book. Returns 201 with the created record.
pub async fn create_book(
    State(state): State<AppState>,
    body: JsonBody,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let input = parse_body(body)?;
    let valid = input.validate().map_err(ApiError::BadRequest)?;
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::insert(&conn, &valid)?;
    Ok((StatusCode::CREATED, Json(book)))
}

/// `GET /books?author=` — list books, optionally filtered by author.
pub async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let author = query
        .author
        .as_deref()
        .map(str::trim)
        .filter(|a| !a.is_empty());
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    let books = db::list(&conn, author)?;
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch a single book.
pub async fn get_book(State(state): State<AppState>, id: IdPath) -> Result<Json<Book>, ApiError> {
    let id = parse_id(id)?;
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::get(&conn, id)?.ok_or(ApiError::NotFound)?;
    Ok(Json(book))
}

/// `PUT /books/{id}` — replace a book's fields. Same validation as create.
pub async fn update_book(
    State(state): State<AppState>,
    id: IdPath,
    body: JsonBody,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(id)?;
    let input = parse_body(body)?;
    let valid = input.validate().map_err(ApiError::BadRequest)?;
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::update(&conn, id, &valid)?.ok_or(ApiError::NotFound)?;
    Ok(Json(book))
}

/// `DELETE /books/{id}` — remove a book. Returns 204 on success.
pub async fn delete_book(
    State(state): State<AppState>,
    id: IdPath,
) -> Result<impl IntoResponse, ApiError> {
    let id = parse_id(id)?;
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if db::delete(&conn, id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound)
    }
}

/// Convert Axum's JSON extraction failure into a 400 with a readable message.
fn parse_body(body: JsonBody) -> Result<BookInput, ApiError> {
    match body {
        Ok(Json(input)) => Ok(input),
        Err(rejection) => Err(ApiError::bad_request(format!(
            "invalid JSON body: {}",
            rejection.body_text()
        ))),
    }
}

/// Convert a non-integer `{id}` path segment into a 400 with a JSON body.
fn parse_id(id: IdPath) -> Result<i64, ApiError> {
    match id {
        Ok(Path(id)) => Ok(id),
        Err(_) => Err(ApiError::bad_request("id must be an integer")),
    }
}
