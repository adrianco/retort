use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde::{Deserialize, Serialize};

use crate::database::Database;
use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Serialize)]
pub struct HealthResponse {
    status: String,
}

pub async fn health() -> impl IntoResponse {
    Json(HealthResponse {
        status: "OK".to_string(),
    })
}

#[derive(Deserialize)]
pub struct ListBooksQuery {
    author: Option<String>,
}

pub async fn list_books(
    State(db): State<Database>,
    query: Option<Query<ListBooksQuery>>,
) -> Result<Json<Vec<Book>>, StatusCode> {
    let author = query.and_then(|q| q.author.clone());
    let books = db.get_books(author.as_deref()).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Database>,
    Path(id): Path<i32>,
) -> Result<Json<Book>, StatusCode> {
    match db.get_book(id).await {
        Ok(Some(book)) => Ok(Json(book)),
        Ok(None) => Err(StatusCode::NOT_FOUND),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

pub async fn create_book(
    State(db): State<Database>,
    Json(book_data): Json<CreateBook>,
) -> Result<Json<Book>, StatusCode> {
    // Validate required fields
    if book_data.title.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if book_data.author.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let book = db.create_book(&book_data).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<Database>,
    Path(id): Path<i32>,
    Json(book_data): Json<UpdateBook>,
) -> Result<Json<Option<Book>>, StatusCode> {
    // Validate that at least one field is provided
    if book_data.title.is_none() && book_data.author.is_none() && book_data.year.is_none() && book_data.isbn.is_none() {
        return Err(StatusCode::BAD_REQUEST);
    }

    // Validate required fields if they are provided
    if let Some(ref title) = book_data.title {
        if title.trim().is_empty() {
            return Err(StatusCode::BAD_REQUEST);
        }
    }
    if let Some(ref author) = book_data.author {
        if author.trim().is_empty() {
            return Err(StatusCode::BAD_REQUEST);
        }
    }

    let book = db.update_book(id, &book_data).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(db): State<Database>,
    Path(id): Path<i32>,
) -> Result<StatusCode, StatusCode> {
    match db.delete_book(id).await {
        Ok(true) => Ok(StatusCode::NO_CONTENT),
        Ok(false) => Err(StatusCode::NOT_FOUND),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}