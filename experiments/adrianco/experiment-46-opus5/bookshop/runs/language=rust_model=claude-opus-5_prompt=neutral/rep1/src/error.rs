use axum::Json;
use axum::extract::rejection::JsonRejection;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde::Serialize;

/// Every failure the API can produce. Each variant maps to exactly one status
/// code so handlers never have to spell one out.
#[derive(Debug)]
pub enum ApiError {
    /// Request body was syntactically fine but semantically invalid.
    Validation(Vec<String>),
    /// Request body could not be read/parsed at all.
    BadRequest(String),
    NotFound(String),
    Internal(String),
}

impl ApiError {
    fn status(&self) -> StatusCode {
        match self {
            ApiError::Validation(_) => StatusCode::UNPROCESSABLE_ENTITY,
            ApiError::BadRequest(_) => StatusCode::BAD_REQUEST,
            ApiError::NotFound(_) => StatusCode::NOT_FOUND,
            ApiError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ApiError::Validation(details) => write!(f, "validation failed: {}", details.join("; ")),
            ApiError::BadRequest(msg) | ApiError::NotFound(msg) | ApiError::Internal(msg) => {
                write!(f, "{msg}")
            }
        }
    }
}

impl std::error::Error for ApiError {}

#[derive(Serialize)]
struct ErrorBody {
    error: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    details: Vec<String>,
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = self.status();
        let body = match self {
            ApiError::Validation(details) => ErrorBody {
                error: "validation failed".to_string(),
                details,
            },
            ApiError::BadRequest(msg) | ApiError::NotFound(msg) => ErrorBody {
                error: msg,
                details: Vec::new(),
            },
            ApiError::Internal(msg) => {
                // The caller gets a generic message; the operator gets the detail.
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
        ApiError::Internal(format!("database error: {err}"))
    }
}

impl From<JsonRejection> for ApiError {
    fn from(rejection: JsonRejection) -> Self {
        ApiError::BadRequest(rejection.body_text())
    }
}
