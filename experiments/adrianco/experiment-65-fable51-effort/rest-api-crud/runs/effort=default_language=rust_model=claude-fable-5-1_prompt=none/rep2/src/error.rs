use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;

/// All error conditions the API can return, each mapped to an HTTP status.
#[derive(Debug)]
pub enum ApiError {
    /// 400 — malformed request body or failed validation.
    BadRequest(Vec<String>),
    /// 404 — no book with the requested id.
    NotFound,
    /// 409 — a unique constraint (isbn) was violated.
    Conflict(String),
    /// 500 — database or other internal failure.
    Internal(String),
}

impl ApiError {
    pub fn bad_request(msg: impl Into<String>) -> Self {
        ApiError::BadRequest(vec![msg.into()])
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        match &e {
            rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
            rusqlite::Error::SqliteFailure(err, _)
                if err.code == rusqlite::ErrorCode::ConstraintViolation =>
            {
                ApiError::Conflict("a book with this isbn already exists".into())
            }
            _ => ApiError::Internal(e.to_string()),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::BadRequest(errors) => (
                StatusCode::BAD_REQUEST,
                json!({ "error": "validation failed", "details": errors }),
            ),
            ApiError::NotFound => (StatusCode::NOT_FOUND, json!({ "error": "book not found" })),
            ApiError::Conflict(msg) => (StatusCode::CONFLICT, json!({ "error": msg })),
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
