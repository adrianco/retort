//! HTTP layer for the book collection API.

pub mod book;

use axum::{
    body::Bytes,
    extract::{Path, Query, State},
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use book::{Book, BookInput};
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::{json, Value};
use std::sync::{Arc, Mutex};

type Db = Arc<Mutex<Connection>>;

/// Builds the router around an open connection. The schema is created here,
/// so the caller only needs to provide a connection.
pub fn app(conn: Connection) -> Router {
    book::init_schema(&conn).expect("failed to initialise schema");
    let db: Db = Arc::new(Mutex::new(conn));

    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

/// Error type that renders as a JSON body with a matching status code.
#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),
    Validation(Vec<String>),
    NotFound,
    Internal,
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": msg })),
            ApiError::Validation(errors) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                json!({ "error": "validation failed", "details": errors }),
            ),
            ApiError::NotFound => (StatusCode::NOT_FOUND, json!({ "error": "book not found" })),
            ApiError::Internal => (
                StatusCode::INTERNAL_SERVER_ERROR,
                json!({ "error": "internal server error" }),
            ),
        };
        (status, Json(body)).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        eprintln!("database error: {err}");
        ApiError::Internal
    }
}

/// Parses and validates a JSON request body.
fn parse_book(body: &Bytes) -> Result<book::NewBook, ApiError> {
    let input: BookInput = serde_json::from_slice(body)
        .map_err(|e| ApiError::BadRequest(format!("invalid JSON body: {e}")))?;
    input.validate().map_err(ApiError::Validation)
}

fn lock(db: &Db) -> std::sync::MutexGuard<'_, Connection> {
    // A poisoned lock only means another request panicked mid-operation;
    // SQLite itself remains consistent, so keep serving.
    db.lock().unwrap_or_else(|e| e.into_inner())
}

async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(State(db): State<Db>, body: Bytes) -> Result<Response, ApiError> {
    let new = parse_book(&body)?;
    let created = book::insert(&lock(&db), &new)?;
    let location = format!("/books/{}", created.id);
    Ok((
        StatusCode::CREATED,
        [(header::LOCATION, location)],
        Json(created),
    )
        .into_response())
}

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = book::list(&lock(&db), q.author.as_deref())?;
    Ok(Json(books))
}

async fn get_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    book::get(&lock(&db), id)?
        .map(Json)
        .ok_or(ApiError::NotFound)
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    body: Bytes,
) -> Result<Json<Book>, ApiError> {
    let new = parse_book(&body)?;
    book::update(&lock(&db), id, &new)?
        .map(Json)
        .ok_or(ApiError::NotFound)
}

async fn delete_book(State(db): State<Db>, Path(id): Path<i64>) -> Result<StatusCode, ApiError> {
    if book::delete(&lock(&db), id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound)
    }
}
