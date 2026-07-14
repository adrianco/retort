use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;
use uuid::Uuid;

use crate::db::Db;
use crate::error::ApiError;
use crate::models::{Book, CreateBook, ListQuery, UpdateBook};

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(db): State<Db>,
    Json(payload): Json<CreateBook>,
) -> Result<impl IntoResponse, ApiError> {
    let title = payload
        .title
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| ApiError::Validation("title is required".into()))?
        .to_string();
    let author = payload
        .author
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| ApiError::Validation("author is required".into()))?
        .to_string();

    let id = Uuid::new_v4().to_string();

    sqlx::query("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)")
        .bind(&id)
        .bind(&title)
        .bind(&author)
        .bind(payload.year)
        .bind(payload.isbn.as_deref())
        .execute(&db)
        .await?;

    let book = Book {
        id,
        title,
        author,
        year: payload.year,
        isbn: payload.isbn,
    };

    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<impl IntoResponse, ApiError> {
    let books: Vec<Book> = if let Some(author) = q.author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY title",
        )
        .bind(author)
        .fetch_all(&db)
        .await?
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY title")
            .fetch_all(&db)
            .await?
    };

    Ok((StatusCode::OK, Json(books)))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_optional(&db)
    .await?
    .ok_or(ApiError::NotFound)?;

    Ok((StatusCode::OK, Json(book)))
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> Result<impl IntoResponse, ApiError> {
    let existing = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_optional(&db)
    .await?
    .ok_or(ApiError::NotFound)?;

    let new_title = match payload.title {
        Some(t) => {
            let trimmed = t.trim().to_string();
            if trimmed.is_empty() {
                return Err(ApiError::Validation("title cannot be empty".into()));
            }
            trimmed
        }
        None => existing.title,
    };
    let new_author = match payload.author {
        Some(a) => {
            let trimmed = a.trim().to_string();
            if trimmed.is_empty() {
                return Err(ApiError::Validation("author cannot be empty".into()));
            }
            trimmed
        }
        None => existing.author,
    };
    let new_year = payload.year.or(existing.year);
    let new_isbn = payload.isbn.or(existing.isbn);

    sqlx::query("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
        .bind(&new_title)
        .bind(&new_author)
        .bind(new_year)
        .bind(new_isbn.as_deref())
        .bind(&id)
        .execute(&db)
        .await?;

    let updated = Book {
        id,
        title: new_title,
        author: new_author,
        year: new_year,
        isbn: new_isbn,
    };

    Ok((StatusCode::OK, Json(updated)))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&db)
        .await?;

    if result.rows_affected() == 0 {
        return Err(ApiError::NotFound);
    }

    Ok(StatusCode::NO_CONTENT)
}
