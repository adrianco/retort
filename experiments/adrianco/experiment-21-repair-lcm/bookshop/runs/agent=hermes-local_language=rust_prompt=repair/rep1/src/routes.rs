use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
    response::IntoResponse,
};

use crate::AppState;

#[derive(Debug)]
pub enum AppResponse {
    Ok(Json<crate::models::Book>),
    OkList(Vec<crate::models::Book>),
    NoContent,
    NotFound,
    BadRequest,
    InternalError,
}

impl IntoResponse for AppResponse {
    fn into_response(self) -> axum::response::Response {
        match self {
            AppResponse::Ok(json) => (StatusCode::OK, json).into_response(),
            AppResponse::OkList(books) => (StatusCode::OK, Json(books)).into_response(),
            AppResponse::NoContent => StatusCode::NO_CONTENT.into_response(),
            AppResponse::NotFound => StatusCode::NOT_FOUND.into_response(),
            AppResponse::BadRequest => StatusCode::BAD_REQUEST.into_response(),
            AppResponse::InternalError => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
        }
    }
}

pub async fn create_book(
    State(state): State<AppState>,
    Json(req): Json<crate::models::CreateBookRequest>,
) -> AppResponse {
    let validation_error = crate::validation::validate_create_request(&req);
    if validation_error.is_some() {
        return AppResponse::BadRequest;
    }

    let db = state.db.lock().unwrap();
    match db.create_book(&req) {
        Ok(book) => AppResponse::Ok(Json(book)),
        Err(_) => AppResponse::InternalError,
    }
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<crate::models::QueryParams>,
) -> AppResponse {
    let db = state.db.lock().unwrap();
    match db.list_books(params.author.as_deref()) {
        Ok(books) => AppResponse::OkList(books),
        Err(_) => AppResponse::InternalError,
    }
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> AppResponse {
    let db = state.db.lock().unwrap();
    match db.get_book(&id) {
        Ok(Some(book)) => AppResponse::Ok(Json(book)),
        Ok(None) => AppResponse::NotFound,
        Err(_) => AppResponse::InternalError,
    }
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(req): Json<crate::models::UpdateBookRequest>,
) -> AppResponse {
    let db = state.db.lock().unwrap();
    match db.update_book(&id, &req) {
        Some(book) => AppResponse::Ok(Json(book)),
        None => AppResponse::NotFound,
    }
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> AppResponse {
    let db = state.db.lock().unwrap();
    match db.delete_book(&id) {
        Ok(true) => AppResponse::NoContent,
        Ok(false) => AppResponse::NotFound,
        Err(_) => AppResponse::InternalError,
    }
}

pub async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "healthy" }))
}
