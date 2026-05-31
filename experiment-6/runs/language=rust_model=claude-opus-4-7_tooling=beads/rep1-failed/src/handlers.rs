use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;
use uuid::Uuid;

use crate::db::DbPool;
use crate::models::{Book, CreateBook, ErrorResponse, ListQuery, UpdateBook};

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(pool): State<DbPool>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), (StatusCode, Json<ErrorResponse>)> {
    let title = match payload.title {
        Some(t) if !t.trim().is_empty() => t,
        _ => {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: "title is required".to_string(),
                }),
            ));
        }
    };
    let author = match payload.author {
        Some(a) if !a.trim().is_empty() => a,
        _ => {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: "author is required".to_string(),
                }),
            ));
        }
    };

    let id = Uuid::new_v4().to_string();
    let book = Book {
        id: id.clone(),
        title,
        author,
        year: payload.year,
        isbn: payload.isbn,
    };

    let result = sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(&book.id)
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(&pool)
    .await;

    match result {
        Ok(_) => Ok((StatusCode::CREATED, Json(book))),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("database error: {}", e),
            }),
        )),
    }
}

pub async fn list_books(
    State(pool): State<DbPool>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, (StatusCode, Json<ErrorResponse>)> {
    let books: Result<Vec<Book>, sqlx::Error> = match q.author {
        Some(author) => {
            sqlx::query_as::<_, Book>(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY title",
            )
            .bind(author)
            .fetch_all(&pool)
            .await
        }
        None => {
            sqlx::query_as::<_, Book>(
                "SELECT id, title, author, year, isbn FROM books ORDER BY title",
            )
            .fetch_all(&pool)
            .await
        }
    };

    match books {
        Ok(b) => Ok(Json(b)),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("database error: {}", e),
            }),
        )),
    }
}

pub async fn get_book(
    State(pool): State<DbPool>,
    Path(id): Path<String>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_optional(&pool)
    .await;

    match book {
        Ok(Some(b)) => Ok(Json(b)),
        Ok(None) => Err((
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                error: "book not found".to_string(),
            }),
        )),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("database error: {}", e),
            }),
        )),
    }
}

pub async fn update_book(
    State(pool): State<DbPool>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, (StatusCode, Json<ErrorResponse>)> {
    let existing = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_optional(&pool)
    .await;

    let mut current = match existing {
        Ok(Some(b)) => b,
        Ok(None) => {
            return Err((
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "book not found".to_string(),
                }),
            ));
        }
        Err(e) => {
            return Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("database error: {}", e),
                }),
            ));
        }
    };

    if let Some(title) = payload.title {
        if title.trim().is_empty() {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: "title cannot be empty".to_string(),
                }),
            ));
        }
        current.title = title;
    }
    if let Some(author) = payload.author {
        if author.trim().is_empty() {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: "author cannot be empty".to_string(),
                }),
            ));
        }
        current.author = author;
    }
    if payload.year.is_some() {
        current.year = payload.year;
    }
    if payload.isbn.is_some() {
        current.isbn = payload.isbn;
    }

    let result = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&current.title)
    .bind(&current.author)
    .bind(current.year)
    .bind(&current.isbn)
    .bind(&current.id)
    .execute(&pool)
    .await;

    match result {
        Ok(_) => Ok(Json(current)),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("database error: {}", e),
            }),
        )),
    }
}

pub async fn delete_book(
    State(pool): State<DbPool>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&pool)
        .await;

    match result {
        Ok(r) if r.rows_affected() == 0 => Err((
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                error: "book not found".to_string(),
            }),
        )),
        Ok(_) => Ok(StatusCode::NO_CONTENT),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("database error: {}", e),
            }),
        )),
    }
}
