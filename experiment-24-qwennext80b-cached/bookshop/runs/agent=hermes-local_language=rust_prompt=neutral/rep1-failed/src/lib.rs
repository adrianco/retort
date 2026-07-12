use actix_web::{web, HttpResponse, Result};
use rusqlite::OptionalExtension;
use serde::{Deserialize, Serialize};
use std::env;
use std::sync::Arc;
use tokio::sync::Mutex;

pub type DbPool = Arc<Mutex<rusqlite::Connection>>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateBook {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

// Error types
#[derive(thiserror::Error, Debug)]
pub enum BookError {
    #[error("Not found")]
    NotFound,
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Database error: {0}")]
    Database(String),
}

impl actix_web::ResponseError for BookError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        match self {
            BookError::NotFound => actix_web::http::StatusCode::NOT_FOUND,
            BookError::Validation(_) => actix_web::http::StatusCode::BAD_REQUEST,
            BookError::Database(_) => actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

impl From<rusqlite::Error> for BookError {
    fn from(err: rusqlite::Error) -> Self {
        BookError::Database(err.to_string())
    }
}

// Health check endpoint
pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "healthy"}))
}

// Initialize database pool
pub async fn init_pool() -> DbPool {
    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string());
    let conn = rusqlite::Connection::open(&database_url).expect("Failed to connect to database");
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )"
    ).expect("Failed to create table");
    
    Arc::new(Mutex::new(conn))
}

// Get all books (with optional author filter)
pub async fn get_books(
    pool: web::Data<DbPool>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> Result<HttpResponse, BookError> {
    let author_filter = query.get("author").cloned();
    
    let conn = pool.lock().await;
    
    let books = if let Some(author) = author_filter {
        let mut stmt = conn.prepare("SELECT * FROM books WHERE author = ?1")?;
        let books: Vec<Book> = stmt.query_map([&author], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })?.collect::<Result<_, _>>()?;
        
        books
    } else {
        let mut stmt = conn.prepare("SELECT * FROM books")?;
        let books: Vec<Book> = stmt.query_map([], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })?.collect::<Result<_, _>>()?;
        
        books
    };
    
    Ok(HttpResponse::Ok().json(books))
}

// Get single book by ID
pub async fn get_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
) -> Result<HttpResponse, BookError> {
    let book_id = path.into_inner();
    
    let conn = pool.lock().await;
    
    let book = conn.query_row(
        "SELECT * FROM books WHERE id = ?1",
        [&book_id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        }
    );
    
    match book {
        Ok(b) => Ok(HttpResponse::Ok().json(b)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Err(BookError::NotFound),
        Err(e) => Err(BookError::Database(e.to_string())),
    }
}

// Create a new book
pub async fn create_book(
    pool: web::Data<DbPool>,
    book: web::Json<CreateBook>,
) -> Result<HttpResponse, BookError> {
    // Validate required fields
    if book.title.is_empty() {
        return Err(BookError::Validation("Title is required".to_string()));
    }
    if book.author.is_empty() {
        return Err(BookError::Validation("Author is required".to_string()));
    }
    
    let conn = pool.lock().await;
    
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![&book.title, &book.author, &book.year, &book.isbn],
    )?;
    
    let id = conn.last_insert_rowid();
    
    let created_book = conn.query_row(
        "SELECT * FROM books WHERE id = ?1",
        [&id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        }
    )?;
    
    Ok(HttpResponse::Created().json(created_book))
}

// Update a book
pub async fn update_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
    book: web::Json<UpdateBook>,
) -> Result<HttpResponse, BookError> {
    let book_id = path.into_inner();
    let conn = pool.lock().await;
    
    // Check if book exists
    let exists = conn.query_row(
        "SELECT COUNT(*) FROM books WHERE id = ?1",
        [&book_id],
        |row| row.get::<_, i64>(0)
    ).optional()?;
    
    if exists.is_none() {
        return Err(BookError::NotFound);
    }
    
    // Build dynamic update query
    let mut params: Vec<&dyn rusqlite::ToSql> = Vec::new();
    let mut sets = Vec::new();
    
    if let Some(title) = &book.title {
        sets.push("title = ?");
        params.push(title);
    }
    if let Some(author) = &book.author {
        sets.push("author = ?");
        params.push(author);
    }
    if let Some(year) = &book.year {
        sets.push("year = ?");
        params.push(year);
    }
    if let Some(isbn) = &book.isbn {
        sets.push("isbn = ?");
        params.push(isbn);
    }
    
    if !sets.is_empty() {
        params.push(&book_id);
        let query = format!("UPDATE books SET {} WHERE id = ?", sets.join(", "));
        conn.execute(&query, rusqlite::params_from_iter(params.iter()))?;
    }
    
    // Return updated book
    let updated_book = conn.query_row(
        "SELECT * FROM books WHERE id = ?1",
        [&book_id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        }
    )?;
    
    Ok(HttpResponse::Ok().json(updated_book))
}

// Delete a book
pub async fn delete_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
) -> Result<HttpResponse, BookError> {
    let book_id = path.into_inner();
    let conn = pool.lock().await;
    
    // Check if book exists
    let exists = conn.query_row(
        "SELECT COUNT(*) FROM books WHERE id = ?1",
        [&book_id],
        |row| row.get::<_, i64>(0)
    ).optional()?;
    
    if exists.is_none() {
        return Err(BookError::NotFound);
    }
    
    conn.execute("DELETE FROM books WHERE id = ?1", [&book_id])?;
    
    Ok(HttpResponse::NoContent().finish())
}
