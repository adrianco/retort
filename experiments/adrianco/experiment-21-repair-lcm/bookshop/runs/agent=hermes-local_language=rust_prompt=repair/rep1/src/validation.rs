use axum::http::StatusCode;

use crate::models::CreateBookRequest;

pub fn validate_create_request(req: &CreateBookRequest) -> Option<StatusCode> {
    if req.title.is_none() || req.title.as_ref().map(|s| s.trim().is_empty()).unwrap_or(true) {
        return Some(StatusCode::BAD_REQUEST);
    }
    if req.author.is_none() || req.author.as_ref().map(|s| s.trim().is_empty()).unwrap_or(true) {
        return Some(StatusCode::BAD_REQUEST);
    }
    None
}
