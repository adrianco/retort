use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post, put, delete},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::net::TcpListener;

mod database;

use database::{Database, Book};

#[derive(Debug, Serialize, Deserialize)]
struct BookRequest {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BookResponse {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl From<Book> for BookResponse {
    fn from(book: Book) -> Self {
        BookResponse {
            id: book.id.unwrap(),
            title: book.title,
            author: book.author,
            year: book.year,
            isbn: book.isbn,
        }
    }
}

impl From<BookRequest> for Book {
    fn from(request: BookRequest) -> Self {
        Book {
            id: None,
            title: request.title,
            author: request.author,
            year: request.year,
            isbn: request.isbn,
        }
    }
}

async fn health_check() -> impl IntoResponse {
    StatusCode::OK
}

async fn create_book(
    State(db): State<Arc<Database>>,
    Json(book_request): Json<BookRequest>,
) -> Result<impl IntoResponse, StatusCode> {
    // Validate required fields
    if book_request.title.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if book_request.author.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let book = Book::from(book_request);
    let created_book = db.create_book(&book).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let response = BookResponse::from(created_book);
    
    Ok((StatusCode::CREATED, Json(response)))
}

async fn get_book(
    State(db): State<Arc<Database>>,
    Path(id): Path<i64>,
) -> Result<impl IntoResponse, StatusCode> {
    let book = db.get_book(id).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    match book {
        Some(book) => {
            let response = BookResponse::from(book);
            Ok(Json(response))
        }
        None => Err(StatusCode::NOT_FOUND),
    }
}

async fn list_books(
    State(db): State<Arc<Database>>,
    author: Option<String>,
) -> Result<impl IntoResponse, StatusCode> {
    let books = db.list_books(author.as_deref()).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let responses: Vec<BookResponse> = books.into_iter().map(BookResponse::from).collect();
    
    Ok(Json(responses))
}

async fn update_book(
    State(db): State<Arc<Database>>,
    Path(id): Path<i64>,
    Json(book_request): Json<BookRequest>,
) -> Result<impl IntoResponse, StatusCode> {
    // Validate required fields
    if book_request.title.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if book_request.author.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let book = Book::from(book_request);
    let updated_book = db.update_book(id, &book).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    match updated_book {
        Some(book) => {
            let response = BookResponse::from(book);
            Ok(Json(response))
        }
        None => Err(StatusCode::NOT_FOUND),
    }
}

async fn delete_book(
    State(db): State<Arc<Database>>,
    Path(id): Path<i64>,
) -> Result<impl IntoResponse, StatusCode> {
    let deleted = db.delete_book(id).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize the database
    let db = Database::new("sqlite::memory:").await?;
    let db = Arc::new(db);

    // Create the router
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/:id", get(get_book))
        .route("/books/:id", put(update_book))
        .route("/books/:id", delete(delete_book))
        .with_state(db);

    // Start the server
    let listener = TcpListener::bind("127.0.0.1:3000").await?;
    println!("Server running on http://127.0.0.1:3000");
    axum::serve(listener, app).await?;

    Ok(())
}