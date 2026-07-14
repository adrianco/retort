use actix_web::{web, App, HttpServer, HttpResponse, Result, Responder, web::Json, web::Path, get, post, put, delete};
use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};
use std::env;
use uuid::Uuid;
use env_logger;

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

// Initialize database and create books table
async fn init_db() -> Result<SqlitePool, sqlx::Error> {
    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite::memory:".to_string());
    let pool = SqlitePool::connect(&database_url).await?;
    
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )
        "#
    ).execute(&pool).await?;
    
    Ok(pool)
}

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(HealthResponse {
        status: "OK".to_string(),
    })
}

#[post("/books")]
async fn create_book(
    pool: web::Data<SqlitePool>,
    book_data: Json<BookInput>
) -> Result<impl Responder> {
    // Validate input
    if book_data.title.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Title is required"));
    }
    if book_data.author.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Author is required"));
    }
    
    let id = Uuid::new_v4().to_string();
    let book = Book {
        id: Some(id.clone()),
        title: book_data.title.clone(),
        author: book_data.author.clone(),
        year: book_data.year,
        isbn: book_data.isbn.clone(),
    };
    
    let result = sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES (?, ?, ?, ?, ?)
        "#)
        .bind(&book.id)
        .bind(&book.title)
        .bind(&book.author)
        .bind(book.year)
        .bind(&book.isbn)
        .execute(&**pool)
        .await;
    
    match result {
        Ok(_) => Ok(HttpResponse::Created().json(book)),
        Err(e) => {
            eprintln!("Database error: {}", e);
            Ok(HttpResponse::InternalServerError().json("Database error"))
        }
    }
}

#[get("/books")]
async fn get_books(
    pool: web::Data<SqlitePool>,
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<impl Responder> {
    let author_filter = query.get("author").map(|s| s.to_string());
    
    let mut sql = "SELECT * FROM books".to_string();
    let mut params = Vec::new();
    
    if let Some(author) = &author_filter {
        sql += " WHERE author = ?";
        params.push(author.clone());
    }
    
    sql += " ORDER BY title";
    
    let mut rows = sqlx::query(&sql);
    for param in &params {
        rows = rows.bind(param);
    }
    
    let books: Vec<Book> = rows
        .fetch_all(&**pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            actix_web::error::ErrorInternalServerError("Database error")
        })?
        .into_iter()
        .map(|row| Book {
            id: Some(row.get("id")),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        })
        .collect();
    
    Ok(HttpResponse::Ok().json(books))
}

#[get("/books/{id}")]
async fn get_book(
    pool: web::Data<SqlitePool>,
    path: Path<String>
) -> Result<impl Responder> {
    let id = path.into_inner();
    
    let book = sqlx::query(
        "SELECT * FROM books WHERE id = ?"
    )
    .bind(&id)
    .fetch_one(&**pool)
    .await;
    
    match book {
        Ok(row) => {
            let book = Book {
                id: Some(row.get("id")),
                title: row.get("title"),
                author: row.get("author"),
                year: row.get("year"),
                isbn: row.get("isbn"),
            };
            Ok(HttpResponse::Ok().json(book))
        }
        Err(sqlx::Error::RowNotFound) => {
            Ok(HttpResponse::NotFound().json("Book not found"))
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Ok(HttpResponse::InternalServerError().json("Database error"))
        }
    }
}

#[put("/books/{id}")]
async fn update_book(
    pool: web::Data<SqlitePool>,
    path: Path<String>,
    book_data: Json<BookInput>
) -> Result<impl Responder> {
    let id = path.into_inner();
    
    // Validate input
    if book_data.title.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Title is required"));
    }
    if book_data.author.is_empty() {
        return Ok(HttpResponse::BadRequest().json("Author is required"));
    }
    
    let result = sqlx::query(
        r#"
        UPDATE books 
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
        "#)
        .bind(&book_data.title)
        .bind(&book_data.author)
        .bind(book_data.year)
        .bind(&book_data.isbn)
        .bind(&id)
        .execute(&**pool)
        .await;
    
    match result {
        Ok(rows_affected) => {
            if rows_affected.rows_affected() == 0 {
                Ok(HttpResponse::NotFound().json("Book not found"))
            } else {
                let updated_book = Book {
                    id: Some(id),
                    title: book_data.title.clone(),
                    author: book_data.author.clone(),
                    year: book_data.year,
                    isbn: book_data.isbn.clone(),
                };
                Ok(HttpResponse::Ok().json(updated_book))
            }
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Ok(HttpResponse::InternalServerError().json("Database error"))
        }
    }
}

#[delete("/books/{id}")]
async fn delete_book(
    pool: web::Data<SqlitePool>,
    path: Path<String>
) -> Result<impl Responder> {
    let id = path.into_inner();
    
    let result = sqlx::query(
        "DELETE FROM books WHERE id = ?"
    )
    .bind(&id)
    .execute(&**pool)
    .await;
    
    match result {
        Ok(rows_affected) => {
            if rows_affected.rows_affected() == 0 {
                Ok(HttpResponse::NotFound().json("Book not found"))
            } else {
                Ok(HttpResponse::NoContent().finish())
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
    env::set_var("RUST_LOG", "debug");
    env_logger::init();
    
    let pool = init_db().await.expect("Failed to initialize database");
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .service(health)
            .service(create_book)
            .service(get_books)
            .service(get_book)
            .service(update_book)
            .service(delete_book)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
