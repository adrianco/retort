use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};
use std::collections::HashMap;
use std::net::SocketAddr;
use uuid::Uuid;
use warp::Filter;

#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: Option<String>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

// Initialize the database connection
async fn init_db() -> Result<SqlitePool, sqlx::Error> {
    // Create the database file if it doesn't exist
    let pool = SqlitePool::connect("sqlite:books.db").await?;
    
    // Create the books table
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"
    ).execute(&pool).await?;
    
    Ok(pool)
}

// Get all books (with optional filter)
async fn get_books(
    pool: SqlitePool,
    author_filter: Option<String>
) -> Result<impl warp::Reply, warp::Rejection> {
    // The query building is now handled differently to avoid the Send issue
    let query = if let Some(author) = author_filter {
        sqlx::query("SELECT * FROM books WHERE author = ? ORDER BY title")
            .bind(author)
    } else {
        sqlx::query("SELECT * FROM books ORDER BY title")
    };
    
    let rows = query.fetch_all(&pool)
        .await
        .map_err(|_| warp::reject::custom(DbError))?;
    
    let mut books: Vec<Book> = Vec::new();
    
    for row in rows {
        let id: String = row.get("id");
        let title: String = row.get("title");
        let author: String = row.get("author");
        let year: Option<i32> = row.get("year");
        let isbn: Option<String> = row.get("isbn");
        
        books.push(Book {
            id: Some(id),
            title,
            author,
            year,
            isbn,
        });
    }
    
    Ok(warp::reply::json(&books))
}

// Get a single book by ID
async fn get_book(
    pool: SqlitePool,
    id: String
) -> Result<impl warp::Reply, warp::Rejection> {
    let row = sqlx::query("SELECT * FROM books WHERE id = ?")
        .bind(&id)
        .fetch_one(&pool)
        .await
        .map_err(|_| warp::reject::custom(BookNotFoundError))?;
    
    let id: String = row.get("id");
    let title: String = row.get("title");
    let author: String = row.get("author");
    let year: Option<i32> = row.get("year");
    let isbn: Option<String> = row.get("isbn");
    
    let book = Book {
        id: Some(id),
        title,
        author,
        year,
        isbn,
    };
    
    Ok(warp::reply::json(&book))
}

// Create a new book
async fn create_book(
    pool: SqlitePool,
    book_input: BookInput
) -> Result<impl warp::Reply, warp::Rejection> {
    // Validate required fields
    if book_input.title.is_empty() {
        return Err(warp::reject::custom(ValidationError::MissingTitle));
    }
    if book_input.author.is_empty() {
        return Err(warp::reject::custom(ValidationError::MissingAuthor));
    }
    
    let id = Uuid::new_v4().to_string();
    
    sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
    )
    .bind(&id)
    .bind(&book_input.title)
    .bind(&book_input.author)
    .bind(book_input.year)
    .bind(book_input.isbn.as_deref())
    .execute(&pool)
    .await
    .map_err(|_| warp::reject::custom(DbError))?;
    
    let book = Book {
        id: Some(id),
        title: book_input.title,
        author: book_input.author,
        year: book_input.year,
        isbn: book_input.isbn,
    };
    
    // Return the created book with ID
    Ok(warp::reply::with_status(warp::reply::json(&book), warp::http::StatusCode::CREATED))
}

// Update a book
async fn update_book(
    pool: SqlitePool,
    id: String,
    book_input: BookInput
) -> Result<impl warp::Reply, warp::Rejection> {
    // Validate required fields
    if book_input.title.is_empty() {
        return Err(warp::reject::custom(ValidationError::MissingTitle));
    }
    if book_input.author.is_empty() {
        return Err(warp::reject::custom(ValidationError::MissingAuthor));
    }
    
    // Check if book exists
    let row = sqlx::query("SELECT id FROM books WHERE id = ?")
        .bind(&id)
        .fetch_one(&pool)
        .await
        .map_err(|_| warp::reject::custom(BookNotFoundError))?;
    
    // Update the book
    sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    )
    .bind(&book_input.title)
    .bind(&book_input.author)
    .bind(book_input.year)
    .bind(book_input.isbn.as_deref())
    .bind(&id)
    .execute(&pool)
    .await
    .map_err(|_| warp::reject::custom(DbError))?;
    
    let book = Book {
        id: Some(id),
        title: book_input.title,
        author: book_input.author,
        year: book_input.year,
        isbn: book_input.isbn,
    };
    
    Ok(warp::reply::json(&book))
}

// Delete a book
async fn delete_book(
    pool: SqlitePool,
    id: String
) -> Result<impl warp::Reply, warp::Rejection> {
    // Check if book exists
    let row = sqlx::query("SELECT id FROM books WHERE id = ?")
        .bind(&id)
        .fetch_one(&pool)
        .await
        .map_err(|_| warp::reject::custom(BookNotFoundError))?;
    
    // Delete the book
    sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&pool)
        .await
        .map_err(|_| warp::reject::custom(DbError))?;
    
    Ok(warp::reply::with_status(warp::reply::json(&"Book deleted successfully"), warp::http::StatusCode::NO_CONTENT))
}

// Health check endpoint
async fn health_check() -> Result<impl warp::Reply, warp::Rejection> {
    let response = HealthResponse {
        status: "healthy".to_string(),
    };
    Ok(warp::reply::json(&response))
}

// Error handling
#[derive(Debug)]
struct DbError;

impl warp::reject::Reject for DbError {}

#[derive(Debug)]
struct BookNotFoundError;

impl warp::reject::Reject for BookNotFoundError {}

#[derive(Debug)]
struct InvalidUuidError;

impl warp::reject::Reject for InvalidUuidError {}

#[derive(Debug)]
enum ValidationError {
    MissingTitle,
    MissingAuthor,
}

impl warp::reject::Reject for ValidationError {}

// Custom error response for validation errors
impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            ValidationError::MissingTitle => write!(f, "Title is required"),
            ValidationError::MissingAuthor => write!(f, "Author is required"),
        }
    }
}

// Custom error response for validation errors
impl std::error::Error for ValidationError {}

#[tokio::main]
async fn main() {
    // Initialize database
    let pool = init_db().await.expect("Failed to initialize database");
    
    // Define routes using the approach that avoids Send issues
    let health = warp::path("health").and(warp::get()).and_then(health_check);
    
    let books_get = warp::path("books")
        .and(warp::get())
        .and(warp::query::<HashMap<String, String>>())
        .and(with_db(pool.clone()))
        .and_then(|params: HashMap<String, String>, pool: SqlitePool| async move {
            let author = params.get("author").cloned();
            get_books(pool, author).await
        });
    
    let books_get_by_id = warp::path("books")
        .and(warp::path::param::<String>())
        .and(warp::get())
        .and(with_db(pool.clone()))
        .and_then(|id: String, pool: SqlitePool| async move {
            get_book(pool, id).await
        });
    
    let books_post = warp::path("books")
        .and(warp::post())
        .and(warp::body::json())
        .and(with_db(pool.clone()))
        .and_then(|book_input: BookInput, pool: SqlitePool| async move {
            create_book(pool, book_input).await
        });
    
    let books_put = warp::path("books")
        .and(warp::path::param::<String>())
        .and(warp::put())
        .and(warp::body::json())
        .and(with_db(pool.clone()))
        .and_then(|id: String, book_input: BookInput, pool: SqlitePool| async move {
            update_book(pool, id, book_input).await
        });
    
    let books_delete = warp::path("books")
        .and(warp::path::param::<String>())
        .and(warp::delete())
        .and(with_db(pool.clone()))
        .and_then(|id: String, pool: SqlitePool| async move {
            delete_book(pool, id).await
        });
    
    // Combine all routes
    let routes = books_get
        .or(books_get_by_id)
        .or(books_post)
        .or(books_put)
        .or(books_delete)
        .or(health);
    
    // Start the server
    let addr = SocketAddr::from(([127, 0, 0, 1], 3030));
    println!("Server starting on http://{}", addr);
    warp::serve(routes).run(addr).await;
}

// Helper function to add database pool to the request context
fn with_db(pool: SqlitePool) -> impl Filter<Extract = (SqlitePool,), Error = std::convert::Infallible> + Clone {
    warp::any().map(move || pool.clone())
}
