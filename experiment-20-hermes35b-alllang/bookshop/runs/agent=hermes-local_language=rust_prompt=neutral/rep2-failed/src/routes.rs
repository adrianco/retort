use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
    response::IntoResponse,
    routing::{delete, get, post, put},
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;
use tracing::info;

use crate::db;
use crate::models::{CreateBookRequest, UpdateBookRequest};

#[derive(Debug, Serialize)]
struct ApiResponse {
    success: bool,
    data: Option<serde_json::Value>,
    message: Option<String>,
    error: Option<String>,
}

impl ApiResponse {
    fn ok(data: serde_json::Value) -> Self {
        Self {
            success: true,
            data: Some(data),
            message: None,
            error: None,
        }
    }

    fn created(data: serde_json::Value) -> Self {
        Self {
            success: true,
            data: Some(data),
            message: Some("Book created successfully".to_string()),
            error: None,
        }
    }

    fn deleted() -> Self {
        Self {
            success: true,
            data: None,
            message: Some("Book deleted successfully".to_string()),
            error: None,
        }
    }
}

#[derive(Debug)]
struct ErrorResp {
    success: bool,
    message: String,
    status: StatusCode,
}

impl IntoResponse for ErrorResp {
    fn into_response(self) -> axum::response::Response {
        let resp = ApiResponse {
            success: self.success,
            data: None,
            message: Some(self.message.clone()),
            error: Some(self.message),
        };
        (self.status, Json(resp)).into_response()
    }
}

#[derive(Debug, Deserialize)]
pub struct FilterParams {
    pub author: Option<String>,
}

pub fn create_router(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book_handler))
        .route("/books/{id}", put(update_book_handler))
        .route("/books/{id}", delete(delete_book_handler))
        .with_state(pool)
}

async fn health_check() -> impl IntoResponse {
    Json(ApiResponse::ok(serde_json::json!({ "status": "ok" })))
}

async fn create_book(
    State(pool): State<SqlitePool>,
    Json(req): Json<CreateBookRequest>,
) -> impl IntoResponse {
    if let Err(e) = req.validate() {
        return ErrorResp {
            success: false,
            message: e,
            status: StatusCode::BAD_REQUEST,
        }
        .into_response();
    }

    let id = uuid::Uuid::new_v4().to_string();
    let title = req.title.trim().to_string();
    let author = req.author.trim().to_string();
    let year = req.year.unwrap_or(0);
    let isbn = req
        .isbn
        .as_deref()
        .unwrap_or("")
        .trim()
        .to_string();

    match db::create_book(&pool, &id, &title, &author, year, &isbn).await {
        Ok(book) => {
            info!("Created book: {}", id);
            (StatusCode::CREATED, Json(ApiResponse::created(
                serde_json::to_value(&book).unwrap(),
            ))).into_response()
        }
        Err(e) => ErrorResp {
            success: false,
            message: e,
            status: StatusCode::INTERNAL_SERVER_ERROR,
        }.into_response(),
    }
}

async fn list_books(
    State(pool): State<SqlitePool>,
    Query(params): Query<FilterParams>,
) -> impl IntoResponse {
    match db::list_books(&pool, params.author.as_deref()).await {
        Ok(books) => {
            info!("Listed {} books", books.len());
            (StatusCode::OK, Json(ApiResponse::ok(
                serde_json::to_value(&books).unwrap(),
            ))).into_response()
        }
        Err(e) => ErrorResp {
            success: false,
            message: e,
            status: StatusCode::INTERNAL_SERVER_ERROR,
        }.into_response(),
    }
}

async fn get_book_handler(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match db::get_book(&pool, &id).await {
        Ok(book) => {
            info!("Got book: {}", id);
            (StatusCode::OK, Json(ApiResponse::ok(
                serde_json::to_value(&book).unwrap(),
            ))).into_response()
        }
        Err(e) => ErrorResp {
            success: false,
            message: e,
            status: StatusCode::NOT_FOUND,
        }.into_response(),
    }
}

async fn update_book_handler(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
    Json(req): Json<UpdateBookRequest>,
) -> impl IntoResponse {
    match db::update_book(&pool, &id, &req).await {
        Ok(book) => {
            info!("Updated book: {}", id);
            (StatusCode::OK, Json(ApiResponse::ok(
                serde_json::to_value(&book).unwrap(),
            ))).into_response()
        }
        Err(e) => ErrorResp {
            success: false,
            message: e,
            status: StatusCode::NOT_FOUND,
        }.into_response(),
    }
}

async fn delete_book_handler(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match db::delete_book(&pool, &id).await {
        Ok(()) => {
            info!("Deleted book: {}", id);
            (StatusCode::OK, Json(ApiResponse::deleted())).into_response()
        }
        Err(e) => ErrorResp {
            success: false,
            message: e,
            status: StatusCode::NOT_FOUND,
        }.into_response(),
    }
}
