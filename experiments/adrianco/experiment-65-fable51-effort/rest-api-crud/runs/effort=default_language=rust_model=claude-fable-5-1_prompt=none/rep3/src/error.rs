//! API error type that maps to JSON responses with appropriate status codes.

use axum::{
    extract::rejection::JsonRejection,
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};

use crate::models::ErrorBody;

#[derive(Debug)]
pub enum ApiError {
    /// 400: the request body was malformed or failed validation.
    BadRequest(String, Option<Vec<String>>),
    /// 404: the requested book does not exist.
    NotFound,
    /// 409: a uniqueness constraint (ISBN) was violated.
    Conflict(String),
    /// 500: something went wrong on the server.
    Internal(String),
}

impl ApiError {
    pub fn validation(details: Vec<String>) -> Self {
        ApiError::BadRequest("validation failed".to_string(), Some(details))
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        match &err {
            rusqlite::Error::SqliteFailure(e, _)
                if e.code == rusqlite::ErrorCode::ConstraintViolation =>
            {
                ApiError::Conflict("a book with this isbn already exists".to_string())
            }
            rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
            _ => ApiError::Internal(err.to_string()),
        }
    }
}

impl From<JsonRejection> for ApiError {
    fn from(rej: JsonRejection) -> Self {
        ApiError::BadRequest(rej.body_text(), None)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::BadRequest(msg, details) => (
                StatusCode::BAD_REQUEST,
                ErrorBody {
                    error: msg,
                    details,
                },
            ),
            ApiError::NotFound => (
                StatusCode::NOT_FOUND,
                ErrorBody {
                    error: "book not found".to_string(),
                    details: None,
                },
            ),
            ApiError::Conflict(msg) => (
                StatusCode::CONFLICT,
                ErrorBody {
                    error: msg,
                    details: None,
                },
            ),
            ApiError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    ErrorBody {
                        error: "internal server error".to_string(),
                        details: None,
                    },
                )
            }
        };
        (status, Json(body)).into_response()
    }
}
