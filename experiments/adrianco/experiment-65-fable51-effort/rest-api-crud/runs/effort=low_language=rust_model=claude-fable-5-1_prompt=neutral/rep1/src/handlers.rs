//! HTTP handlers.

use crate::{db, AppState};
use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::Deserialize;
use serde_json::json;

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// Validated form of BookInput.
struct ValidBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

fn error(status: StatusCode, msg: impl Into<String>) -> Response {
    (status, Json(json!({ "error": msg.into() }))).into_response()
}

fn validate(input: Result<Json<BookInput>, JsonRejection>) -> Result<ValidBook, Response> {
    let Json(input) = input.map_err(|e| error(StatusCode::BAD_REQUEST, e.body_text()))?;

    let title = input.title.map(|s| s.trim().to_string()).unwrap_or_default();
    if title.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "title is required"));
    }
    let author = input.author.map(|s| s.trim().to_string()).unwrap_or_default();
    if author.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "author is required"));
    }
    if let Some(y) = input.year {
        if !(0..=9999).contains(&y) {
            return Err(error(StatusCode::BAD_REQUEST, "year must be between 0 and 9999"));
        }
    }
    let isbn = input.isbn.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    if let Some(i) = &isbn {
        let digits = i.chars().filter(|c| c.is_ascii_digit() || *c == 'X').count();
        if digits != 10 && digits != 13 {
            return Err(error(StatusCode::BAD_REQUEST, "isbn must contain 10 or 13 digits"));
        }
    }
    Ok(ValidBook { title, author, year: input.year, isbn })
}

fn db_error(e: rusqlite::Error) -> Response {
    error(StatusCode::INTERNAL_SERVER_ERROR, format!("database error: {e}"))
}

pub async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

pub async fn create_book(
    State(state): State<AppState>,
    input: Result<Json<BookInput>, JsonRejection>,
) -> Response {
    let b = match validate(input) {
        Ok(b) => b,
        Err(r) => return r,
    };
    let conn = state.lock().unwrap();
    match db::insert(&conn, &b.title, &b.author, b.year, b.isbn.as_deref()) {
        Ok(book) => (StatusCode::CREATED, Json(book)).into_response(),
        Err(e) => db_error(e),
    }
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Response {
    let conn = state.lock().unwrap();
    match db::list(&conn, q.author.as_deref()) {
        Ok(books) => Json(books).into_response(),
        Err(e) => db_error(e),
    }
}

pub async fn get_book(State(state): State<AppState>, Path(id): Path<i64>) -> Response {
    let conn = state.lock().unwrap();
    match db::get(&conn, id) {
        Ok(Some(book)) => Json(book).into_response(),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => db_error(e),
    }
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    input: Result<Json<BookInput>, JsonRejection>,
) -> Response {
    let b = match validate(input) {
        Ok(b) => b,
        Err(r) => return r,
    };
    let conn = state.lock().unwrap();
    match db::update(&conn, id, &b.title, &b.author, b.year, b.isbn.as_deref()) {
        Ok(Some(book)) => Json(book).into_response(),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => db_error(e),
    }
}

pub async fn delete_book(State(state): State<AppState>, Path(id): Path<i64>) -> Response {
    let conn = state.lock().unwrap();
    match db::delete(&conn, id) {
        Ok(true) => StatusCode::NO_CONTENT.into_response(),
        Ok(false) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => db_error(e),
    }
}
