use axum::http::StatusCode;
use axum::response::IntoResponse;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// --- Models ---

#[derive(Debug, Deserialize, Serialize)]
pub struct BookCreate {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<Option<i32>>,
    pub isbn: Option<Option<String>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BookResponse {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

// --- Error types ---

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Validation error: {0}")]
    ValidationError(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Database error: {0}")]
    DatabaseError(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, message) = match self {
            AppError::ValidationError(msg) => (StatusCode::UNPROCESSABLE_ENTITY, msg),
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg),
            AppError::DatabaseError(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };

        let body = serde_json::json!({ "error": message });
        (status, axum::Json(body)).into_response()
    }
}

// --- Database ---

use sqlx::sqlite::SqlitePool;
use sqlx::FromRow;

#[derive(Debug, FromRow)]
pub struct BookRecord {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

pub async fn get_pool() -> Result<SqlitePool, sqlx::Error> {
    let pool = SqlitePool::connect("sqlite://books.db").await?;
    Ok(pool)
}

pub async fn create_test_pool() -> SqlitePool {
    SqlitePool::connect("sqlite::memory:").await.unwrap()
}

// --- Handlers ---

#[cfg(test)]
mod tests;

use std::sync::Arc;
use axum::extract::{Path, Query};
use axum::routing::{delete, get, post, put};
use axum::{Extension, Json, Router};
use tower_http::trace::TraceLayer;

pub fn create_router(pool: SqlitePool) -> Router {
    let state = Arc::new(pool);

    Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book))
        .route("/books/{id}", put(update_book))
        .route("/books/{id}", delete(delete_book))
        .layer(Extension(state))
        .layer(TraceLayer::new_for_http())
}

async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

async fn create_book(
    Extension(pool): Extension<Arc<SqlitePool>>,
    Json(input): Json<BookCreate>,
) -> Result<Json<BookResponse>, AppError> {
    if input.title.is_empty() {
        return Err(AppError::ValidationError("title is required".to_string()));
    }
    if input.author.is_empty() {
        return Err(AppError::ValidationError("author is required".to_string()));
    }

    let id = uuid::Uuid::new_v4().to_string();
    let now = chrono::Utc::now().to_rfc3339();

    sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)",
    )
    .bind(&id)
    .bind(&input.title)
    .bind(&input.author)
    .bind(input.year)
    .bind(&input.isbn)
    .bind(&now)
    .bind(&now)
    .execute(&*pool)
    .await
    .map_err(|e| AppError::DatabaseError(e.to_string()))?;

    Ok(Json(BookResponse {
        id,
        title: input.title,
        author: input.author,
        year: input.year,
        isbn: input.isbn,
        created_at: now.clone(),
        updated_at: now,
    }))
}

async fn list_books(
    Extension(pool): Extension<Arc<SqlitePool>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<BookResponse>>, AppError> {
    let author_filter: Option<String> = params.get("author").cloned();

    let records: Vec<BookRecord> = if let Some(ref author) = author_filter {
        sqlx::query_as::<_, BookRecord>(
            "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ? ORDER BY id",
        )
        .bind(author)
        .fetch_all(&*pool)
        .await
        .map_err(|e| AppError::DatabaseError(e.to_string()))?
    } else {
        sqlx::query_as::<_, BookRecord>(
            "SELECT id, title, author, year, isbn, created_at, updated_at FROM books ORDER BY id",
        )
        .fetch_all(&*pool)
        .await
        .map_err(|e| AppError::DatabaseError(e.to_string()))?
    };

    Ok(Json(
        records
            .into_iter()
            .map(|r| BookResponse {
                id: r.id,
                title: r.title,
                author: r.author,
                year: r.year,
                isbn: r.isbn,
                created_at: r.created_at,
                updated_at: r.updated_at,
            })
            .collect(),
    ))
}

async fn get_book(
    Extension(pool): Extension<Arc<SqlitePool>>,
    Path(id): Path<String>,
) -> Result<Json<BookResponse>, AppError> {
    let record = sqlx::query_as::<_, BookRecord>(
        "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_one(&*pool)
    .await
    .map_err(|e| match e {
        sqlx::Error::RowNotFound => AppError::NotFound(format!("Book with id '{}' not found", id)),
        _ => AppError::DatabaseError(e.to_string()),
    })?;

    Ok(Json(BookResponse {
        id: record.id,
        title: record.title,
        author: record.author,
        year: record.year,
        isbn: record.isbn,
        created_at: record.created_at,
        updated_at: record.updated_at,
    }))
}

async fn update_book(
    Extension(pool): Extension<Arc<SqlitePool>>,
    Path(id): Path<String>,
    Json(input): Json<BookUpdate>,
) -> Result<Json<BookResponse>, AppError> {
    let existing: Option<BookRecord> =
        sqlx::query_as::<_, BookRecord>(
            "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?",
        )
        .bind(&id)
        .fetch_optional(&*pool)
        .await
        .map_err(|e| AppError::DatabaseError(e.to_string()))?;

    let book = existing.ok_or_else(|| AppError::NotFound(format!("Book with id '{}' not found", id)))?;

    let title = input.title.or(Some(book.title.clone()));
    if title.as_ref().map(|s| s.is_empty()).unwrap_or(false) {
        return Err(AppError::ValidationError("title is required".to_string()));
    }

    let author = input.author.or(Some(book.author.clone()));
    if author.as_ref().map(|s| s.is_empty()).unwrap_or(false) {
        return Err(AppError::ValidationError("author is required".to_string()));
    }

    let now = chrono::Utc::now().to_rfc3339();

    let record = sqlx::query_as::<_, BookRecord>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?
         RETURNING id, title, author, year, isbn, created_at, updated_at",
    )
    .bind(&title.unwrap())
    .bind(&author.unwrap())
    .bind(input.year)
    .bind(&input.isbn)
    .bind(&now)
    .bind(&id)
    .fetch_one(&*pool)
    .await
    .map_err(|e| AppError::DatabaseError(e.to_string()))?;

    Ok(Json(BookResponse {
        id: record.id,
        title: record.title,
        author: record.author,
        year: record.year,
        isbn: record.isbn,
        created_at: record.created_at,
        updated_at: record.updated_at,
    }))
}

async fn delete_book(
    Extension(pool): Extension<Arc<SqlitePool>>,
    Path(id): Path<String>,
) -> Result<StatusCode, AppError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&*pool)
        .await
        .map_err(|e| AppError::DatabaseError(e.to_string()))?;

    if result.rows_affected() == 0 {
        return Err(AppError::NotFound(format!("Book with id '{}' not found", id)));
    }

    Ok(StatusCode::NO_CONTENT)
}
