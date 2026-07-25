use actix_web::{web, App, HttpResponse, Result};
use serde::Deserialize;
use validator::Validate;

use crate::{
    AppError, CreateBookRequest, HealthResponse, UpdateBookRequest, BookRepository,
};

#[derive(Deserialize)]
pub struct QueryParams {
    author: Option<String>,
}

pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(HealthResponse::ok())
}

pub async fn get_books(
    query: web::Query<QueryParams>,
    data: web::Data<BookRepository>,
) -> Result<HttpResponse, AppError> {
    let books = data.get_books(query.author.clone()).await?;
    Ok(HttpResponse::Ok().json(books))
}

pub async fn get_book(
    path: web::Path<i64>,
    data: web::Data<BookRepository>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    let book = data.get_book_by_id(id).await?;
    Ok(HttpResponse::Ok().json(book))
}

pub async fn create_book(
    web::Json(req): web::Json<CreateBookRequest>,
    data: web::Data<BookRepository>,
) -> Result<HttpResponse, AppError> {
    req.validate().map_err(|e| {
        AppError::Validation(format!("Validation error: {}", e))
    })?;
    
    let book = data.create_book(&req).await?;
    Ok(HttpResponse::Created().json(book))
}

pub async fn update_book(
    path: web::Path<i64>,
    web::Json(req): web::Json<UpdateBookRequest>,
    data: web::Data<BookRepository>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    
    if let Some(ref title) = req.title {
        if title.is_empty() {
            return Err(AppError::Validation("title cannot be empty".to_string()));
        }
    }
    if let Some(ref author) = req.author {
        if author.is_empty() {
            return Err(AppError::Validation("author cannot be empty".to_string()));
        }
    }
    if let Some(ref isbn) = req.isbn {
        if isbn.is_empty() {
            return Err(AppError::Validation("isbn cannot be empty".to_string()));
        }
    }
    
    let book = data.update_book(id, &req).await?;
    Ok(HttpResponse::Ok().json(book))
}

pub async fn delete_book(
    path: web::Path<i64>,
    data: web::Data<BookRepository>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    data.delete_book(id).await?;
    Ok(HttpResponse::NoContent().finish())
}
