pub mod db;

use std::sync::{Arc, Mutex};

use axum::{
    extract::{
        rejection::{JsonRejection, PathRejection, QueryRejection},
        Path, Query, State,
    },
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::json;

use db::{Book, BookFields};

type Db = Arc<Mutex<Connection>>;

/// Builds the router around an already-initialised database connection.
pub fn app(conn: Connection) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .fallback(|| async { ApiError::NotFound("resource not found".into()) })
        .with_state(Arc::new(Mutex::new(conn)))
}

#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),
    Validation(Vec<String>),
    NotFound(String),
    Internal,
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": msg })),
            ApiError::Validation(details) => (
                StatusCode::BAD_REQUEST,
                json!({ "error": "validation failed", "details": details }),
            ),
            ApiError::NotFound(msg) => (StatusCode::NOT_FOUND, json!({ "error": msg })),
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

/// Request body for create and update. Everything is optional at the serde
/// level so that missing fields are reported by `validate` rather than as an
/// opaque deserialization failure.
#[derive(Debug, Deserialize)]
struct BookInput {
    title: Option<String>,
    author: Option<String>,
    year: Option<i64>,
    isbn: Option<String>,
}

impl BookInput {
    fn validate(self) -> Result<BookFields, ApiError> {
        let mut errors = Vec::new();
        let title = self.title.map(|t| t.trim().to_string()).unwrap_or_default();
        let author = self.author.map(|a| a.trim().to_string()).unwrap_or_default();
        if title.is_empty() {
            errors.push("title is required".to_string());
        }
        if author.is_empty() {
            errors.push("author is required".to_string());
        }
        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                errors.push("year must be between 0 and 9999".to_string());
            }
        }
        let isbn = self
            .isbn
            .map(|i| i.trim().to_string())
            .filter(|i| !i.is_empty());
        if !errors.is_empty() {
            return Err(ApiError::Validation(errors));
        }
        Ok(BookFields {
            title,
            author,
            year: self.year,
            isbn,
        })
    }
}

fn parse_body(body: Result<Json<BookInput>, JsonRejection>) -> Result<BookFields, ApiError> {
    let Json(input) = body.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    input.validate()
}

fn parse_id(id: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    id.map(|Path(id)| id)
        .map_err(|_| ApiError::BadRequest("book id must be an integer".into()))
}

fn not_found(id: i64) -> ApiError {
    ApiError::NotFound(format!("book {id} not found"))
}

/// Runs a database operation on the blocking pool so SQLite I/O never stalls
/// the async runtime.
async fn with_db<T, F>(db: Db, f: F) -> Result<T, ApiError>
where
    F: FnOnce(&Connection) -> rusqlite::Result<T> + Send + 'static,
    T: Send + 'static,
{
    tokio::task::spawn_blocking(move || {
        // A poisoned lock only means another request panicked; the
        // connection itself is still usable.
        let conn = db.lock().unwrap_or_else(|e| e.into_inner());
        f(&conn)
    })
    .await
    .map_err(|_| ApiError::Internal)?
    .map_err(ApiError::from)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

#[derive(Debug, Deserialize)]
struct ListParams {
    author: Option<String>,
}

async fn list_books(
    State(db): State<Db>,
    params: Result<Query<ListParams>, QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let Query(params) = params.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    let books = with_db(db, move |conn| db::list(conn, params.author.as_deref())).await?;
    Ok(Json(books))
}

async fn create_book(
    State(db): State<Db>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let fields = parse_body(body)?;
    let book = with_db(db, move |conn| db::insert(conn, &fields)).await?;
    let location = format!("/books/{}", book.id);
    Ok((
        StatusCode::CREATED,
        [(axum::http::header::LOCATION, location)],
        Json(book),
    )
        .into_response())
}

async fn get_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(id)?;
    with_db(db, move |conn| db::get(conn, id))
        .await?
        .map(Json)
        .ok_or_else(|| not_found(id))
}

async fn update_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(id)?;
    let fields = parse_body(body)?;
    with_db(db, move |conn| db::update(conn, id, &fields))
        .await?
        .map(Json)
        .ok_or_else(|| not_found(id))
}

async fn delete_book(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let id = parse_id(id)?;
    if with_db(db, move |conn| db::delete(conn, id)).await? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(not_found(id))
    }
}
