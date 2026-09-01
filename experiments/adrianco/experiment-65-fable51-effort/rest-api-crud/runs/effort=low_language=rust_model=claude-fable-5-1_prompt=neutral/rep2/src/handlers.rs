use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;

use crate::{
    db,
    models::{BookInput, ListQuery},
    AppState,
};

/// Error type mapped to a JSON body and HTTP status.
pub enum ApiError {
    Validation(Vec<String>),
    BadRequest(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::Validation(errors) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                json!({ "error": "validation failed", "details": errors }),
            ),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": msg })),
            ApiError::NotFound => (StatusCode::NOT_FOUND, json!({ "error": "book not found" })),
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    json!({ "error": "internal server error" }),
                )
            }
        };
        (status, Json(body)).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(e.to_string())
    }
}

impl From<JsonRejection> for ApiError {
    fn from(r: JsonRejection) -> Self {
        ApiError::BadRequest(r.body_text())
    }
}

/// Run a closure against the shared connection, converting poison into an error.
fn with_db<T>(
    state: &AppState,
    f: impl FnOnce(&rusqlite::Connection) -> rusqlite::Result<T>,
) -> Result<T, ApiError> {
    let conn = state
        .db
        .lock()
        .map_err(|_| ApiError::Internal("database mutex poisoned".into()))?;
    f(&conn).map_err(ApiError::from)
}

pub async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

pub async fn create_book(
    State(state): State<AppState>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let Json(input) = payload?;
    let valid = input.validate().map_err(ApiError::Validation)?;
    let book = with_db(&state, |c| db::insert(c, &valid))?;
    Ok((StatusCode::CREATED, Json(book)).into_response())
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Response, ApiError> {
    let books = with_db(&state, |c| db::list(c, q.author.as_deref()))?;
    Ok(Json(books).into_response())
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Response, ApiError> {
    let book = with_db(&state, |c| db::get(c, id))?.ok_or(ApiError::NotFound)?;
    Ok(Json(book).into_response())
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let Json(input) = payload?;
    let valid = input.validate().map_err(ApiError::Validation)?;
    let book = with_db(&state, |c| db::update(c, id, &valid))?.ok_or(ApiError::NotFound)?;
    Ok(Json(book).into_response())
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Response, ApiError> {
    let deleted = with_db(&state, |c| db::delete(c, id))?;
    if deleted {
        Ok(StatusCode::NO_CONTENT.into_response())
    } else {
        Err(ApiError::NotFound)
    }
}
