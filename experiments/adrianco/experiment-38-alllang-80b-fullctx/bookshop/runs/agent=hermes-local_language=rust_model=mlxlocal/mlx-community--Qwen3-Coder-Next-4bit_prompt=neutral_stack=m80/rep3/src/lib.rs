use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use thiserror::Error;
use validator::Validate;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Book not found")]
    NotFound,
}

impl actix_web::ResponseError for AppError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        match self {
            AppError::Database(_) => actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Validation(_) => actix_web::http::StatusCode::BAD_REQUEST,
            AppError::NotFound => actix_web::http::StatusCode::NOT_FOUND,
        }
    }

    fn error_response(&self) -> actix_web::HttpResponse {
        actix_web::HttpResponse::build(self.status_code()).json(serde_json::json!({
            "error": self.to_string()
        }))
    }
}

#[derive(Debug, Serialize, FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: u32,
    pub isbn: String,
}

#[derive(Debug, Deserialize, Validate)]
pub struct CreateBookRequest {
    #[validate(length(min = 1, message = "title is required"))]
    pub title: String,
    #[validate(length(min = 1, message = "author is required"))]
    pub author: String,
    pub year: u32,
    #[validate(length(min = 1, message = "isbn is required"))]
    pub isbn: String,
}

#[derive(Debug, Deserialize, Validate)]
pub struct UpdateBookRequest {
    #[validate(length(min = 1, message = "title cannot be empty"))]
    pub title: Option<String>,
    #[validate(length(min = 1, message = "author cannot be empty"))]
    pub author: Option<String>,
    pub year: Option<u32>,
    #[validate(length(min = 1, message = "isbn cannot be empty"))]
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
}

impl HealthResponse {
    pub fn ok() -> Self {
        HealthResponse {
            status: "healthy".to_string(),
        }
    }
}

pub mod api;
pub mod repository;

pub use api::*;
pub use repository::*;
