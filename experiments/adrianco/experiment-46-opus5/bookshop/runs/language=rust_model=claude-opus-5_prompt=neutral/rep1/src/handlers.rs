use axum::Json;
use axum::extract::{FromRequest, Path, Query, Request, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};

use crate::db;
use crate::error::ApiError;
use crate::models::{Book, BookPayload};
use crate::state::AppState;

/// `axum::Json` with our error shape: a malformed body should still come back
/// as `{"error": ...}` rather than plain text.
pub struct ApiJson<T>(pub T);

impl<S, T> FromRequest<S> for ApiJson<T>
where
    S: Send + Sync,
    T: DeserializeOwned,
{
    type Rejection = ApiError;

    async fn from_request(req: Request, state: &S) -> Result<Self, Self::Rejection> {
        let Json(value) = Json::<T>::from_request(req, state).await?;
        Ok(ApiJson(value))
    }
}

#[derive(Serialize)]
pub struct Health {
    status: &'static str,
    books: i64,
}

/// `GET /health` — also proves the database is reachable, not just that the
/// process is up.
pub async fn health(State(state): State<AppState>) -> Result<Json<Health>, ApiError> {
    let books = state
        .with_conn(|conn| {
            Ok(conn.query_row("SELECT COUNT(*) FROM books", [], |row| row.get::<_, i64>(0))?)
        })
        .await?;

    Ok(Json(Health {
        status: "ok",
        books,
    }))
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    author: Option<String>,
}

/// `GET /books` with an optional `?author=` filter.
pub async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = state
        .with_conn(move |conn| db::list(conn, query.author.as_deref()))
        .await?;
    Ok(Json(books))
}

/// `POST /books`
pub async fn create_book(
    State(state): State<AppState>,
    ApiJson(payload): ApiJson<BookPayload>,
) -> Result<Response, ApiError> {
    let book = payload.validate()?;
    let created = state.with_conn(move |conn| db::insert(conn, &book)).await?;

    let location = format!("/books/{}", created.id);
    Ok((
        StatusCode::CREATED,
        [(axum::http::header::LOCATION, location)],
        Json(created),
    )
        .into_response())
}

/// `GET /books/{id}`
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(&id)?;
    let book = state.with_conn(move |conn| db::get(conn, id)).await?;
    book.map(Json).ok_or_else(|| not_found_book(id))
}

/// `PUT /books/{id}` — a full replacement, so the same validation as create.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    ApiJson(payload): ApiJson<BookPayload>,
) -> Result<Json<Book>, ApiError> {
    let id = parse_id(&id)?;
    let book = payload.validate()?;
    let updated = state
        .with_conn(move |conn| db::update(conn, id, &book))
        .await?;
    updated.map(Json).ok_or_else(|| not_found_book(id))
}

/// `DELETE /books/{id}`
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let id = parse_id(&id)?;
    let deleted = state.with_conn(move |conn| db::delete(conn, id)).await?;
    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(not_found_book(id))
    }
}

pub async fn not_found() -> ApiError {
    ApiError::NotFound("no such route".to_string())
}

/// Ids come off the path as text so a bad one yields a JSON 400 instead of
/// axum's plain-text path rejection.
fn parse_id(raw: &str) -> Result<i64, ApiError> {
    raw.parse::<i64>()
        .map_err(|_| ApiError::BadRequest(format!("invalid book id: {raw:?}")))
}

fn not_found_book(id: i64) -> ApiError {
    ApiError::NotFound(format!("book {id} not found"))
}
