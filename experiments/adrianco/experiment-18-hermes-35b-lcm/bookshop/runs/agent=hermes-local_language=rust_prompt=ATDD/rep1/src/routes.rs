use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    json::Json,
    response::IntoResponse,
    routing::{delete, get, post, put},
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;
use uuid::Uuid;

use crate::db;
use crate::models::{CreateBookRequest, UpdateBookRequest};

pub fn create_router(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book).get(list_books))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(pool)
}

async fn health_check() -> impl IntoResponse {
    StatusCode::OK
}

async fn create_book(
    State(pool): State<SqlitePool>,
    Json(req): Json<CreateBookRequest>,
) -> Result<impl IntoResponse, AppError> {
    if req.title.is_none() || req.title.as_ref().unwrap().is_empty() {
        return Err(AppError::Validation("title is required".to_string()));
    }
    if req.author.is_none() || req.author.as_ref().unwrap().is_empty() {
        return Err(AppError::Validation("author is required".to_string()));
    }

    let book = db::create_book(&pool, &req).await?;
    Ok((StatusCode::CREATED, Json(book)))
}

#[derive(Deserialize)]
pub struct ListBooksQuery {
    author: Option<String>,
}

async fn list_books(
    State(pool): State<SqlitePool>,
    Query(params): Query<ListBooksQuery>,
) -> impl IntoResponse {
    let books = db::list_books(&pool, params.author.as_deref()).await.unwrap_or_default();
    (StatusCode::OK, Json(books))
}

async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, AppError> {
    let uuid = Uuid::parse_str(&id).map_err(|_| AppError::NotFound)?;
    let book = db::get_book(&pool, uuid).await?;
    match book {
        Some(b) => Ok((StatusCode::OK, Json(b))),
        None => Err(AppError::NotFound),
    }
}

async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
    Json(req): Json<UpdateBookRequest>,
) -> Result<impl IntoResponse, AppError> {
    let uuid = Uuid::parse_str(&id).map_err(|_| AppError::NotFound)?;
    let book = db::update_book(&pool, uuid, &req).await?;
    match book {
        Some(b) => Ok((StatusCode::OK, Json(b))),
        None => Err(AppError::NotFound),
    }
}

async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, AppError> {
    let uuid = Uuid::parse_str(&id).map_err(|_| AppError::NotFound)?;
    let deleted = db::delete_book(&pool, uuid).await?;
    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(AppError::NotFound)
    }
}

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("validation error: {0}")]
    Validation(String),
    #[error("not found")]
    NotFound,
    #[error("database error")]
    Database,
}

impl IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        match self {
            AppError::Validation(msg) => {
                let body = serde_json::json!({"error": msg});
                (StatusCode::BAD_REQUEST, Json(body)).into_response()
            }
            AppError::NotFound => StatusCode::NOT_FOUND.into_response(),
            AppError::Database => {
                let body = serde_json::json!({"error": "internal server error"});
                (StatusCode::INTERNAL_SERVER_ERROR, Json(body)).into_response()
            }
        }
    }
}
