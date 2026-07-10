use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;
use warp::{Filter, Rejection, Reply};

// Simple Book structure
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

// In-memory storage for demonstration purposes (production would use proper database)
static mut BOOKS: Option<Vec<Book>> = None;

// Error handling
#[derive(Debug)]
enum BookError {
    BookNotFound,
    InvalidInput(String),
}

impl warp::reject::Reject for BookError {}

// Custom rejection handler
async fn handle_rejection(err: Rejection) -> Result<impl Reply, Rejection> {
    if err.is_not_found() {
        let json = warp::reply::json(&serde_json::json!({
            "error": "Not found"
        }));
        Ok(warp::reply::with_status(json, warp::http::StatusCode::NOT_FOUND))
    } else if let Some(BookError::BookNotFound) = err.find() {
        let json = warp::reply::json(&serde_json::json!({
            "error": "Book not found"
        }));
        Ok(warp::reply::with_status(json, warp::http::StatusCode::NOT_FOUND))
    } else if let Some(BookError::InvalidInput(msg)) = err.find() {
        let json = warp::reply::json(&serde_json::json!({
            "error": msg
        }));
        Ok(warp::reply::with_status(json, warp::http::StatusCode::BAD_REQUEST))
    } else {
        eprintln!("Unhandled error: {:?}", err);
        let json = warp::reply::json(&serde_json::json!({
            "error": "Internal server error"
        }));
        Ok(warp::reply::with_status(json, warp::http::StatusCode::INTERNAL_SERVER_ERROR))
    }
}

// Routes
async fn get_books(author: Option<String>) -> Result<impl Reply, Rejection> {
    unsafe {
        if let Some(books) = &BOOKS {
            if let Some(author_filter) = author {
                let filtered: Vec<Book> = books
                    .iter()
                    .filter(|book| book.author == author_filter)
                    .cloned()
                    .collect();
                Ok(warp::reply::json(&filtered))
            } else {
                Ok(warp::reply::json(books))
            }
        } else {
            Ok(warp::reply::json(&Vec::<Book>::new()))
        }
    }
}

async fn get_book_by_id(id: String) -> Result<impl Reply, Rejection> {
    unsafe {
        if let Some(books) = &BOOKS {
            if let Some(book) = books.iter().find(|book| book.id == id) {
                Ok(warp::reply::json(book))
            } else {
                Err(warp::reject::custom(BookError::BookNotFound))
            }
        } else {
            Err(warp::reject::custom(BookError::BookNotFound))
        }
    }
}

async fn create_book(book: Book) -> Result<impl Reply, Rejection> {
    // Validate required fields
    if book.title.is_empty() {
        return Err(warp::reject::custom(BookError::InvalidInput("Title is required".to_string())));
    }
    if book.author.is_empty() {
        return Err(warp::reject::custom(BookError::InvalidInput("Author is required".to_string())));
    }

    unsafe {
        if BOOKS.is_none() {
            BOOKS = Some(Vec::new());
        }
        if let Some(books) = &mut BOOKS {
            books.push(book.clone());
            Ok(warp::reply::with_status(warp::reply::json(&book), warp::http::StatusCode::CREATED))
        } else {
            Err(warp::reject::custom(BookError::InvalidInput("Failed to create book".to_string())))
        }
    }
}

async fn update_book(id: String, book: Book) -> Result<impl Reply, Rejection> {
    // Validate required fields
    if book.title.is_empty() {
        return Err(warp::reject::custom(BookError::InvalidInput("Title is required".to_string())));
    }
    if book.author.is_empty() {
        return Err(warp::reject::custom(BookError::InvalidInput("Author is required".to_string())));
    }

    unsafe {
        if let Some(books) = &mut BOOKS {
            if let Some(book_item) = books.iter_mut().find(|b| b.id == id) {
                *book_item = book.clone();
                Ok(warp::reply::json(&book))
            } else {
                Err(warp::reject::custom(BookError::BookNotFound))
            }
        } else {
            Err(warp::reject::custom(BookError::BookNotFound))
        }
    }
}

async fn delete_book(id: String) -> Result<impl Reply, Rejection> {
    unsafe {
        if let Some(books) = &mut BOOKS {
            if let Some(pos) = books.iter().position(|book| book.id == id) {
                books.remove(pos);
                Ok(warp::reply::with_status(warp::reply::json(&"Book deleted successfully"), warp::http::StatusCode::NO_CONTENT))
            } else {
                Err(warp::reject::custom(BookError::BookNotFound))
            }
        } else {
            Err(warp::reject::custom(BookError::BookNotFound))
        }
    }
}

async fn health_check() -> Result<impl Reply, Rejection> {
    let response = HealthResponse {
        status: "OK".to_string(),
    };
    Ok(warp::reply::json(&response))
}

#[tokio::main]
async fn main() {
    // Define routes
    let books = warp::path("books")
        .and(warp::get())
        .and(warp::query::<std::collections::HashMap<String, String>>())
        .and_then(|params: std::collections::HashMap<String, String>| async move {
            let author = params.get("author").cloned();
            get_books(author).await
        });

    let books_post = warp::path("books")
        .and(warp::post())
        .and(warp::body::json())
        .and_then(create_book);

    let books_get_by_id = warp::path("books")
        .and(warp::path::param::<String>())
        .and(warp::get())
        .and_then(get_book_by_id);

    let books_put_by_id = warp::path("books")
        .and(warp::path::param::<String>())
        .and(warp::put())
        .and(warp::body::json())
        .and_then(update_book);

    let books_delete_by_id = warp::path("books")
        .and(warp::path::param::<String>())
        .and(warp::delete())
        .and_then(delete_book);

    let health = warp::path("health")
        .and(warp::get())
        .and_then(|| async { health_check().await });

    let routes = books
        .or(books_post)
        .or(books_get_by_id)
        .or(books_put_by_id)
        .or(books_delete_by_id)
        .or(health)
        .recover(handle_rejection);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3030));
    println!("Server starting on http://{}", addr);
    println!("API endpoints:");
    println!("  GET    /health");
    println!("  GET    /books");
    println!("  GET    /books/{{id}}");
    println!("  POST   /books");
    println!("  PUT    /books/{{id}}");
    println!("  DELETE /books/{{id}}");
    println!("  Filter by author: GET /books?author=AuthorName");
    
    warp::serve(routes).run(addr).await;
}