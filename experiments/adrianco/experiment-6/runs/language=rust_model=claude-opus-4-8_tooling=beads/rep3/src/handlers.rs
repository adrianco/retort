use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde::Deserialize;
use serde_json::json;

use crate::db::Db;
use crate::models::BookInput;

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// GET /health
pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

/// POST /books
pub async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> impl IntoResponse {
    let book = match input.validate() {
        Ok(b) => b,
        Err(e) => return error(StatusCode::BAD_REQUEST, &e),
    };
    match db.create(&book) {
        Ok(created) => (StatusCode::CREATED, Json(json!(created))).into_response(),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

/// GET /books?author=
pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> impl IntoResponse {
    match db.list(q.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(json!(books))).into_response(),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

/// GET /books/{id}
pub async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> impl IntoResponse {
    match db.get(id) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))).into_response(),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

/// PUT /books/{id}
pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> impl IntoResponse {
    let book = match input.validate() {
        Ok(b) => b,
        Err(e) => return error(StatusCode::BAD_REQUEST, &e),
    };
    match db.update(id, &book) {
        Ok(Some(updated)) => (StatusCode::OK, Json(json!(updated))).into_response(),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

/// DELETE /books/{id}
pub async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> impl IntoResponse {
    match db.delete(id) {
        Ok(true) => StatusCode::NO_CONTENT.into_response(),
        Ok(false) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(e) => error(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string()),
    }
}

fn error(status: StatusCode, message: &str) -> axum::response::Response {
    (status, Json(json!({ "error": message }))).into_response()
}
