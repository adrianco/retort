//! API error type that maps to JSON responses with proper HTTP status codes.

use axum::extract::rejection::{JsonRejection, PathRejection};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Serialize;

#[derive(Debug)]
pub enum ApiError {
    NotFound(String),
    Validation(Vec<String>),
    BadRequest(String),
    Conflict(String),
    Internal(String),
}

#[derive(Serialize)]
struct ErrorBody {
    error: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    details: Vec<String>,
}

impl ApiError {
    fn status(&self) -> StatusCode {
        match self {
            ApiError::NotFound(_) => StatusCode::NOT_FOUND,
            ApiError::Validation(_) => StatusCode::UNPROCESSABLE_ENTITY,
            ApiError::BadRequest(_) => StatusCode::BAD_REQUEST,
            ApiError::Conflict(_) => StatusCode::CONFLICT,
            ApiError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = self.status();
        let body = match self {
            ApiError::Validation(details) => ErrorBody {
                error: "validation failed".to_string(),
                details,
            },
            ApiError::NotFound(msg)
            | ApiError::BadRequest(msg)
            | ApiError::Conflict(msg) => ErrorBody {
                error: msg,
                details: Vec::new(),
            },
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                ErrorBody {
                    error: "internal server error".to_string(),
                    details: Vec::new(),
                }
            }
        };
        (status, Json(body)).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        match err {
            rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound("book not found".into()),
            rusqlite::Error::SqliteFailure(e, msg)
                if e.code == rusqlite::ErrorCode::ConstraintViolation =>
            {
                ApiError::Conflict(msg.unwrap_or_else(|| "constraint violation".into()))
            }
            other => ApiError::Internal(other.to_string()),
        }
    }
}

impl From<JsonRejection> for ApiError {
    fn from(rej: JsonRejection) -> Self {
        ApiError::BadRequest(rej.body_text())
    }
}

impl From<PathRejection> for ApiError {
    fn from(rej: PathRejection) -> Self {
        ApiError::BadRequest(rej.body_text())
    }
}
