use actix_web::{web, App, HttpResponse, HttpServer, Result, get, post, put, delete};
use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row, QueryBuilder};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: Option<String>,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Serialize, Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

async fn health() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(HealthResponse { status: "healthy".to_string() }))
}

async fn create_book(
    pool: web::Data<SqlitePool>,
    book_data: web::Json<BookInput>
) -> Result<HttpResponse> {
    // Validate input
    if book_data.title.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Title is required"));
    }
    if book_data.author.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Author is required"));
    }

    let id = Uuid::new_v4().to_string();
    
    // Use simple query instead of query! macro
    let result = sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
    )
    .bind(&id)
    .bind(&book_data.title)
    .bind(&book_data.author)
    .bind(book_data.year)
    .bind(&book_data.isbn)
    .execute(&pool)
    .await;

    match result {
        Ok(_) => {
            Ok(HttpResponse::Created().json(Book {
                id: Some(id),
                title: book_data.title.clone(),
                author: book_data.author.clone(),
                year: book_data.year,
                isbn: book_data.isbn.clone(),
            }))
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Ok(HttpResponse::InternalServerError().json("Database error"))
        }
    }
}

async fn get_books(
    pool: web::Data<SqlitePool>,
    query: web::Query<HashMap<String, String>>
) -> Result<HttpResponse> {
    let author = query.get("author");
    
    let books = if let Some(author_filter) = author {
        sqlx::query_as!(
            Book,
            "SELECT * FROM books WHERE author = ?",
            author_filter
        )
        .fetch_all(&pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            HttpResponse::InternalServerError().finish()
        })?
    } else {
        sqlx::query_as!(
            Book,
            "SELECT * FROM books"
        )
        .fetch_all(&pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            HttpResponse::InternalServerError().finish()
        })?
    };
    
    Ok(HttpResponse::Ok().json(books))
}

async fn get_book(
    pool: web::Data<SqlitePool>,
    path: web::Path<String>
) -> Result<HttpResponse> {
    let id = path.into_inner();
    
    let book = sqlx::query_as!(
        Book,
        "SELECT * FROM books WHERE id = ?",
        id
    )
    .fetch_optional(&pool)
    .await
    .map_err(|e| {
        eprintln!("Database error: {}", e);
        HttpResponse::InternalServerError().finish()
    })?;
    
    match book {
        Some(book) => Ok(HttpResponse::Ok().json(book)),
        None => Ok(HttpResponse::NotFound().json("Book not found")),
    }
}

async fn update_book(
    pool: web::Data<SqlitePool>,
    path: web::Path<String>,
    book_data: web::Json<BookInput>
) -> Result<HttpResponse> {
    // Validate input
    if book_data.title.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Title is required"));
    }
    if book_data.author.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Author is required"));
    }

    let id = path.into_inner();
    
    let result = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    )
    .bind(&book_data.title)
    .bind(&book_data.author)
    .bind(book_data.year)
    .bind(&book_data.isbn)
    .bind(&id)
    .execute(&pool)
    .await;
    
    match result {
        Ok(result) => {
            if result.rows_affected() == 0 {
                Ok(HttpResponse::NotFound().json("Book not found"))
            } else {
                let book = Book {
                    id: Some(id),
                    title: book_data.title.clone(),
                    author: book_data.author.clone(),
                    year: book_data.year,
                    isbn: book_data.isbn.clone(),
                };
                Ok(HttpResponse::Ok().json(book))
            }
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Ok(HttpResponse::InternalServerError().json("Database error"))
        }
    }
}

async fn delete_book(
    pool: web::Data<SqlitePool>,
    path: web::Path<String>
) -> Result<HttpResponse> {
    let id = path.into_inner();
    
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&pool)
        .await;
        
    match result {
        Ok(result) => {
            if result.rows_affected() == 0 {
                Ok(HttpResponse::NotFound().json("Book not found"))
            } else {
                Ok(HttpResponse::Ok().json("Book deleted"))
            }
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Ok(HttpResponse::InternalServerError().json("Database error"))
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Create database pool
    let pool = SqlitePool::connect("sqlite:books.db").await.unwrap();
    
    // Initialize database
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )"
    )
    .execute(&pool)
    .await
    .unwrap();
    
    println!("Starting server on http://localhost:8080");
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/api/health", web::get().to(health))
            .route("/api/books", web::post().to(create_book))
            .route("/api/books", web::get().to(get_books))
            .route("/api/books/{id}", web::get().to(get_book))
            .route("/api/books/{id}", web::put().to(update_book))
            .route("/api/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
