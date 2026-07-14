use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json},
};
use serde_json::json;
use uuid::Uuid;

use crate::db::{self, Db};
use crate::models::{Book, CreateBook, ErrorResponse, ListQuery, UpdateBook};

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(db): State<Db>,
    Json(input): Json<CreateBook>,
) -> impl IntoResponse {
    let title = match input.title.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()) {
        Some(t) => t.to_string(),
        None => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!(ErrorResponse {
                    error: "title is required".into()
                })),
            )
                .into_response();
        }
    };
    let author = match input.author.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()) {
        Some(a) => a.to_string(),
        None => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!(ErrorResponse {
                    error: "author is required".into()
                })),
            )
                .into_response();
        }
    };

    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };

    match db::insert_book(&db, &book) {
        Ok(_) => (StatusCode::CREATED, Json(json!(book))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse {
                error: format!("db error: {}", e)
            })),
        )
            .into_response(),
    }
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> impl IntoResponse {
    match db::list_books(&db, q.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(json!(books))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse {
                error: format!("db error: {}", e)
            })),
        )
            .into_response(),
    }
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match db::get_book(&db, &id) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))).into_response(),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse {
                error: "book not found".into()
            })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse {
                error: format!("db error: {}", e)
            })),
        )
            .into_response(),
    }
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(input): Json<UpdateBook>,
) -> impl IntoResponse {
    let existing = match db::get_book(&db, &id) {
        Ok(Some(b)) => b,
        Ok(None) => {
            return (
                StatusCode::NOT_FOUND,
                Json(json!(ErrorResponse {
                    error: "book not found".into()
                })),
            )
                .into_response();
        }
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!(ErrorResponse {
                    error: format!("db error: {}", e)
                })),
            )
                .into_response();
        }
    };

    let title = match input.title {
        Some(t) => {
            let t = t.trim().to_string();
            if t.is_empty() {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(json!(ErrorResponse {
                        error: "title must not be empty".into()
                    })),
                )
                    .into_response();
            }
            t
        }
        None => existing.title,
    };
    let author = match input.author {
        Some(a) => {
            let a = a.trim().to_string();
            if a.is_empty() {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(json!(ErrorResponse {
                        error: "author must not be empty".into()
                    })),
                )
                    .into_response();
            }
            a
        }
        None => existing.author,
    };
    let year = input.year.or(existing.year);
    let isbn = input.isbn.or(existing.isbn);

    let updated = Book {
        id: existing.id,
        title,
        author,
        year,
        isbn,
    };

    match db::update_book(&db, &updated) {
        Ok(_) => (StatusCode::OK, Json(json!(updated))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse {
                error: format!("db error: {}", e)
            })),
        )
            .into_response(),
    }
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match db::delete_book(&db, &id) {
        Ok(0) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse {
                error: "book not found".into()
            })),
        )
            .into_response(),
        Ok(_) => StatusCode::NO_CONTENT.into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse {
                error: format!("db error: {}", e)
            })),
        )
            .into_response(),
    }
}
