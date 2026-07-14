use actix_web::{web, HttpResponse};
use sqlx::query;

use crate::{
    error::AppError,
    models::{Book, BooksResponse, CreateBook, UpdateBook},
    DbPool,
};

// Health check endpoint
pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "healthy"}))
}

// Get all books with optional author filter
pub async fn get_books(
    pool: web::Data<DbPool>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> Result<HttpResponse, AppError> {
    let author = query.get("author").cloned();

    let books = if let Some(author) = author {
        sqlx::query_as::<_, Book>(r#"SELECT id, title, author, year, isbn FROM books WHERE author = ?"#)
            .bind(author)
            .fetch_all(pool.get_ref())
            .await?
    } else {
        sqlx::query_as::<_, Book>(r#"SELECT id, title, author, year, isbn FROM books"#)
            .fetch_all(pool.get_ref())
            .await?
    };

    Ok(HttpResponse::Ok().json(BooksResponse { books }))
}

// Get a single book by ID
pub async fn get_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    let book = sqlx::query_as::<_, Book>(r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#)
        .bind(id)
        .fetch_one(pool.get_ref())
        .await
        .map_err(|e| {
            if let sqlx::Error::RowNotFound = e {
                AppError::NotFound(format!("Book with id {} not found", id))
            } else {
                AppError::Database(e)
            }
        })?;

    Ok(HttpResponse::Ok().json(serde_json::json!({"book": book})))
}

// Create a new book
pub async fn create_book(
    pool: web::Data<DbPool>,
    body: web::Json<CreateBook>,
) -> Result<HttpResponse, AppError> {
    let book = body.into_inner();
    
    // Simple validation
    if book.title.is_empty() {
        return Err(AppError::Validation("title is required".to_string()));
    }
    if book.author.is_empty() {
        return Err(AppError::Validation("author is required".to_string()));
    }
    if book.isbn.is_empty() {
        return Err(AppError::Validation("isbn is required".to_string()));
    }

    let result = query(r#"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"#)
        .bind(&book.title)
        .bind(&book.author)
        .bind(book.year)
        .bind(&book.isbn)
        .execute(pool.get_ref())
        .await?;

    let id = result.last_insert_rowid();

    let book = sqlx::query_as::<_, Book>(r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#)
        .bind(id)
        .fetch_one(pool.get_ref())
        .await?;

    Ok(HttpResponse::Created().json(serde_json::json!({"book": book})))
}

// Update a book
pub async fn update_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
    body: web::Json<UpdateBook>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();
    let update = body.into_inner();

    // Check if book exists
    let exists = sqlx::query_scalar::<_, i64>(r#"SELECT COUNT(*) FROM books WHERE id = ?"#)
        .bind(id)
        .fetch_one(pool.get_ref())
        .await?
        > 0;

    if !exists {
        return Err(AppError::NotFound(format!("Book with id {} not found", id)));
    }

    // Clone the options to avoid moves
    let title_opt = update.title.clone();
    let author_opt = update.author.clone();
    let year_opt = update.year.clone();
    let isbn_opt = update.isbn.clone();

    // Use individual queries based on which fields are provided
    match (title_opt, author_opt, year_opt, isbn_opt) {
        (None, None, None, None) => {
            // No fields to update, return the book as-is
            let book = sqlx::query_as::<_, Book>(
                r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#
            )
            .bind(id)
            .fetch_one(pool.get_ref())
            .await?;

            return Ok(HttpResponse::Ok().json(serde_json::json!({"book": book})));
        }
        (Some(title), None, None, None) => {
            sqlx::query(r#"UPDATE books SET title = ? WHERE id = ?"#)
                .bind(&title)
                .bind(id)
                .execute(pool.get_ref())
                .await?;
        }
        (None, Some(author), None, None) => {
            sqlx::query(r#"UPDATE books SET author = ? WHERE id = ?"#)
                .bind(&author)
                .bind(id)
                .execute(pool.get_ref())
                .await?;
        }
        (None, None, Some(year), None) => {
            sqlx::query(r#"UPDATE books SET year = ? WHERE id = ?"#)
                .bind(year)
                .bind(id)
                .execute(pool.get_ref())
                .await?;
        }
        (None, None, None, Some(isbn)) => {
            sqlx::query(r#"UPDATE books SET isbn = ? WHERE id = ?"#)
                .bind(&isbn)
                .bind(id)
                .execute(pool.get_ref())
                .await?;
        }
        _ => {
            // Multiple fields to update
            let title = update.title.unwrap_or_default();
            let author = update.author.unwrap_or_default();
            let year = update.year.unwrap_or(0);
            let isbn = update.isbn.unwrap_or_default();

            let year_str = year.to_string();
            let isbn_str = isbn;

            let mut query_str = String::from("UPDATE books SET ");
            let mut params: Vec<&str> = Vec::new();

            if !title.is_empty() {
                query_str.push_str("title = ?, ");
                params.push(&title);
            }
            if !author.is_empty() {
                query_str.push_str("author = ?, ");
                params.push(&author);
            }
            if year > 0 {
                query_str.push_str("year = ?, ");
                params.push(&year_str);
            }
            if !isbn_str.is_empty() {
                query_str.push_str("isbn = ?, ");
                params.push(&isbn_str);
            }

            // Remove trailing comma and space
            query_str.pop();
            query_str.pop();
            query_str.push_str(" WHERE id = ?");

            let mut query_exec = query(&query_str);
            for p in &params {
                query_exec = query_exec.bind(p);
            }
            query_exec.bind(id).execute(pool.get_ref()).await?;
        }
    }

    let book = sqlx::query_as::<_, Book>(r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?"#)
        .bind(id)
        .fetch_one(pool.get_ref())
        .await?;

    Ok(HttpResponse::Ok().json(serde_json::json!({"book": book})))
}

// Delete a book
pub async fn delete_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
) -> Result<HttpResponse, AppError> {
    let id = path.into_inner();

    let result = query(r#"DELETE FROM books WHERE id = ?"#)
        .bind(id)
        .execute(pool.get_ref())
        .await?;

    let affected = result.rows_affected();

    if affected == 0 {
        return Err(AppError::NotFound(format!("Book with id {} not found", id)));
    }

    Ok(HttpResponse::NoContent().finish())
}
