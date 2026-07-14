use crate::db;
use crate::models::{Book, CreateBook, ErrorResponse, ListQuery, UpdateBook};
use crate::AppState;
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({"status": "ok"})))
}

fn err(status: StatusCode, msg: impl Into<String>) -> Response {
    (status, Json(ErrorResponse { error: msg.into() })).into_response()
}

fn validate_required(title: Option<&str>, author: Option<&str>) -> Result<(String, String), Response> {
    let title = title.map(|s| s.trim()).unwrap_or("");
    let author = author.map(|s| s.trim()).unwrap_or("");
    if title.is_empty() {
        return Err(err(StatusCode::BAD_REQUEST, "title is required"));
    }
    if author.is_empty() {
        return Err(err(StatusCode::BAD_REQUEST, "author is required"));
    }
    Ok((title.to_string(), author.to_string()))
}

pub async fn create_book(
    State(state): State<AppState>,
    Json(body): Json<CreateBook>,
) -> Response {
    let (title, author) = match validate_required(body.title.as_deref(), body.author.as_deref()) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let conn = state.lock().unwrap();
    match db::insert_book(&conn, &title, &author, body.year, body.isbn.as_deref()) {
        Ok(book) => (StatusCode::CREATED, Json(book)).into_response(),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Response {
    let conn = state.lock().unwrap();
    match db::list_books(&conn, q.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(books)).into_response(),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Response {
    let conn = state.lock().unwrap();
    match db::get_book(&conn, id) {
        Ok(Some(book)) => (StatusCode::OK, Json(book)).into_response(),
        Ok(None) => err(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(body): Json<UpdateBook>,
) -> Response {
    let (title, author) = match validate_required(body.title.as_deref(), body.author.as_deref()) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let conn = state.lock().unwrap();
    match db::update_book(&conn, id, &title, &author, body.year, body.isbn.as_deref()) {
        Ok(Some(book)) => (StatusCode::OK, Json::<Book>(book)).into_response(),
        Ok(None) => err(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Response {
    let conn = state.lock().unwrap();
    match db::delete_book(&conn, id) {
        Ok(true) => StatusCode::NO_CONTENT.into_response(),
        Ok(false) => err(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
    }
}
