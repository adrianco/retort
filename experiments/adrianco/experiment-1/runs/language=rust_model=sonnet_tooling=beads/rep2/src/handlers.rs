use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde::Deserialize;
use serde_json::json;
use uuid::Uuid;

use crate::db::{self, DbPool};
use crate::models::{CreateBook, ErrorResponse, UpdateBook};

pub async fn health() -> impl IntoResponse {
    Json(json!({"status": "ok"}))
}

#[derive(Deserialize)]
pub struct AuthorFilter {
    pub author: Option<String>,
}

pub async fn list_books(
    State(pool): State<DbPool>,
    Query(filter): Query<AuthorFilter>,
) -> impl IntoResponse {
    match db::list_books(&pool, filter.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(json!(books))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse::new(e.to_string()))),
        )
            .into_response(),
    }
}

pub async fn create_book(
    State(pool): State<DbPool>,
    Json(payload): Json<CreateBook>,
) -> impl IntoResponse {
    // Validate required fields
    let title = match &payload.title {
        Some(t) if !t.trim().is_empty() => t.trim().to_string(),
        _ => {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!(ErrorResponse::new("title is required"))),
            )
                .into_response()
        }
    };
    let author = match &payload.author {
        Some(a) if !a.trim().is_empty() => a.trim().to_string(),
        _ => {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!(ErrorResponse::new("author is required"))),
            )
                .into_response()
        }
    };

    let validated = CreateBook {
        title: Some(title),
        author: Some(author),
        year: payload.year,
        isbn: payload.isbn,
    };

    let id = Uuid::new_v4().to_string();
    match db::create_book(&pool, &id, &validated) {
        Ok(book) => (StatusCode::CREATED, Json(json!(book))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse::new(e.to_string()))),
        )
            .into_response(),
    }
}

pub async fn get_book(
    State(pool): State<DbPool>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match db::get_book(&pool, &id) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))).into_response(),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse::new("book not found"))),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse::new(e.to_string()))),
        )
            .into_response(),
    }
}

pub async fn update_book(
    State(pool): State<DbPool>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> impl IntoResponse {
    // Validate: if title or author is explicitly provided, must not be empty
    if let Some(t) = &payload.title {
        if t.trim().is_empty() {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!(ErrorResponse::new("title cannot be empty"))),
            )
                .into_response();
        }
    }
    if let Some(a) = &payload.author {
        if a.trim().is_empty() {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!(ErrorResponse::new("author cannot be empty"))),
            )
                .into_response();
        }
    }

    match db::update_book(&pool, &id, &payload) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))).into_response(),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse::new("book not found"))),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse::new(e.to_string()))),
        )
            .into_response(),
    }
}

pub async fn delete_book(
    State(pool): State<DbPool>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match db::delete_book(&pool, &id) {
        Ok(true) => StatusCode::NO_CONTENT.into_response(),
        Ok(false) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse::new("book not found"))),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse::new(e.to_string()))),
        )
            .into_response(),
    }
}
