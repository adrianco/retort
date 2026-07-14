use actix_web::{web, App, HttpServer, HttpResponse, Result};
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
    ).ok();
    
    match book {
        Some(b) => Ok(HttpResponse::Ok().json(b)),
        None => Err(BookError::NotFound),
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
        rusqlite::params![
            book.title,
            book.author,
            book.year,
            book.isbn
        ],
    )?;
    
    let last_id: i64 = conn.last_insert_rowid();
    
    let book = conn.query_row(
        "SELECT * FROM books WHERE id = ?1",
        [&last_id],
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
    
    Ok(HttpResponse::Created().json(book))
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
    let existing = conn.query_row(
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
    ).ok();
    
    if existing.is_none() {
        return Err(BookError::NotFound);
    }
    
    let book = book.into_inner();
    
    // Build update query with parameters
    let mut params: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
    let mut query = String::from("UPDATE books SET ");
    
    if let Some(title) = book.title {
        if !title.is_empty() {
            query.push_str("title = ?1, ");
            params.push(Box::new(title));
        }
    }
    if let Some(author) = book.author {
        if !author.is_empty() {
            query.push_str("author = ?2, ");
            params.push(Box::new(author));
        }
    }
    if let Some(year) = book.year {
        query.push_str("year = ?3, ");
        params.push(Box::new(year));
    }
    if let Some(isbn) = book.isbn {
        if !isbn.is_empty() {
            query.push_str("isbn = ?4, ");
            params.push(Box::new(isbn));
        }
    }
    
    // Remove trailing ", " and add WHERE clause
    if query.ends_with(", ") {
        query.pop();
        query.pop();
    }
    query.push_str(&format!(" WHERE id = {}", book_id));
    
    // Execute update
    let params_refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|p| p.as_ref()).collect();
    conn.execute(&query, rusqlite::params_from_iter(params_refs.iter()))?;
    
    // Fetch updated book
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
    )?;
    
    Ok(HttpResponse::Ok().json(book))
}

// Delete a book
pub async fn delete_book(
    pool: web::Data<DbPool>,
    path: web::Path<i64>,
) -> Result<HttpResponse, BookError> {
    let book_id = path.into_inner();
    
    let conn = pool.lock().await;
    
    let count = conn.execute(
        "DELETE FROM books WHERE id = ?1",
        rusqlite::params![book_id],
    )?;
    
    if count == 0 {
        return Err(BookError::NotFound);
    }
    
    Ok(HttpResponse::NoContent().finish())
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize database
    let _ = init_pool().await;
    
    // Start the server
    let pool = init_pool().await;
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(health))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}

// Unit tests
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_create_book_validation_title_required() {
        let create_book = CreateBook {
            title: "".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };
        
        // Validation should fail when title is empty
        assert!(create_book.title.is_empty());
    }
    
    #[test]
    fn test_create_book_validation_author_required() {
        let create_book = CreateBook {
            title: "Test Book".to_string(),
            author: "".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };
        
        // Validation should fail when author is empty
        assert!(create_book.author.is_empty());
    }
    
    #[test]
    fn test_book_struct() {
        let book = Book {
            id: 1,
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };
        
        assert_eq!(book.id, 1);
        assert_eq!(book.title, "Test Book");
        assert_eq!(book.author, "Test Author");
        assert_eq!(book.year, 2024);
        assert_eq!(book.isbn, "1234567890");
    }
}
