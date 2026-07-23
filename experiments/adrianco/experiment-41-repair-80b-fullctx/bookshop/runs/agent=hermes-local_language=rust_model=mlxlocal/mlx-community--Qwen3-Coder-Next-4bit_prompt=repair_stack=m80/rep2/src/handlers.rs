use actix_web::{web, HttpResponse, Result};
use diesel::prelude::*;

use crate::db::AppState;
use crate::models::{Book, CreateBookRequest, UpdateBookRequest, ListBooksQuery, NewBook};
use crate::schema::books;

// Health check endpoint
pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "healthy"}))
}

// GET /books - List all books (with optional author filter)
pub async fn list_books(
    query: web::Query<ListBooksQuery>,
    data: web::Data<AppState>,
) -> Result<HttpResponse> {
    let mut conn = data.get_connection();
    
    let result = if let Some(author) = &query.author {
        books::table
            .filter(books::author.eq(author.clone()))
            .load::<Book>(&mut conn)
            .map_err(|e| {
                actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
            })?
    } else {
        books::table.load::<Book>(&mut conn).map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
        })?
    };

    Ok(HttpResponse::Ok().json(result))
}

// GET /books/{id} - Get a single book by ID
pub async fn get_book(
    path: web::Path<i32>,
    data: web::Data<AppState>,
) -> Result<HttpResponse> {
    let id = path.into_inner();
    let mut conn = data.get_connection();

    let book = books::table
        .find(id)
        .first::<Book>(&mut conn)
        .optional()
        .map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
        })?;

    match book {
        Some(b) => Ok(HttpResponse::Ok().json(b)),
        None => Ok(HttpResponse::NotFound().json(serde_json::json!({"error": "Book not found"}))),
    }
}

// POST /books - Create a new book
pub async fn create_book(
    body: web::Json<CreateBookRequest>,
    data: web::Data<AppState>,
) -> Result<HttpResponse> {
    let book = body.into_inner();
    
    // Validate required fields
    if book.title.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(serde_json::json!({"error": "Title is required"})));
    }
    if book.author.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(serde_json::json!({"error": "Author is required"})));
    }
    if book.isbn.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(serde_json::json!({"error": "ISBN is required"})));
    }

    let new_book = NewBook {
        title: book.title.clone(),
        author: book.author.clone(),
        year: book.year,
        isbn: book.isbn.clone(),
    };

    let mut conn = data.get_connection();

    diesel::insert_into(books::table)
        .values(&new_book)
        .execute(&mut conn)
        .map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
        })?;

    // Get the created book
    let created_book = books::table
        .order(books::id.desc())
        .first::<Book>(&mut conn)
        .map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
        })?;

    Ok(HttpResponse::Created().json(created_book))
}

// PUT /books/{id} - Update a book
pub async fn update_book(
    path: web::Path<i32>,
    body: web::Json<UpdateBookRequest>,
    data: web::Data<AppState>,
) -> Result<HttpResponse> {
    let id = path.into_inner();
    let updates = body.into_inner();
    let mut conn = data.get_connection();

    // Check if book exists
    let exists = books::table.find(id).first::<Book>(&mut conn).optional().map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
    })?;

    if exists.is_none() {
        return Ok(HttpResponse::NotFound().json(serde_json::json!({"error": "Book not found"})));
    }

    // Build update data as a tuple for diesel
    let update_data = (
        updates.title.map(|t| books::title.eq(t)),
        updates.author.map(|a| books::author.eq(a)),
        updates.year.map(|y| books::year.eq(y)),
        updates.isbn.map(|i| books::isbn.eq(i)),
    );

    diesel::update(books::table.find(id))
        .set(update_data)
        .execute(&mut conn)
        .map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
        })?;

    // Get the updated book
    let updated_book = books::table.find(id).first::<Book>(&mut conn).map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
    })?;

    Ok(HttpResponse::Ok().json(updated_book))
}

// DELETE /books/{id} - Delete a book
pub async fn delete_book(
    path: web::Path<i32>,
    data: web::Data<AppState>,
) -> Result<HttpResponse> {
    let id = path.into_inner();
    let mut conn = data.get_connection();

    let count = diesel::delete(books::table.find(id))
        .execute(&mut conn)
        .map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Database error: {}", e))
        })?;

    if count == 0 {
        Ok(HttpResponse::NotFound().json(serde_json::json!({"error": "Book not found"})))
    } else {
        Ok(HttpResponse::NoContent().finish())
    }
}

pub fn configure_services(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/books")
            .route("", web::get().to(list_books))
            .route("", web::post().to(create_book))
            .route("/{id}", web::get().to(get_book))
            .route("/{id}", web::put().to(update_book))
            .route("/{id}", web::delete().to(delete_book))
    );
    cfg.service(web::resource("/health").route(web::get().to(health)));
}
