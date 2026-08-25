use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Unexpected error: {0}")]
    Unexpected(String),
}

impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, message) = match &self {
            AppError::Database(err) => (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                err.to_string(),
            ),
            AppError::Validation(msg) => (axum::http::StatusCode::BAD_REQUEST, msg.clone()),
            AppError::NotFound(msg) => (axum::http::StatusCode::NOT_FOUND, msg.clone()),
            AppError::Unexpected(msg) => {
                (axum::http::StatusCode::INTERNAL_SERVER_ERROR, msg.clone())
            }
        };
        (status, serde_json::json!({ "error": message })).into_response()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: u32,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<u32>,
    pub isbn: Option<String>,
}

impl BookInput {
    pub fn validate(&self) -> Result<(), AppError> {
        if self.title.trim().is_empty() {
            return Err(AppError::Validation("title is required".to_string()));
        }
        if self.author.trim().is_empty() {
            return Err(AppError::Validation("author is required".to_string()));
        }
        Ok(())
    }
}
