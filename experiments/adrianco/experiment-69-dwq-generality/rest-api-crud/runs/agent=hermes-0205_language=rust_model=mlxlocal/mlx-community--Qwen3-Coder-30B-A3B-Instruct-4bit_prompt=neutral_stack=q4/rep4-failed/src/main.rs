use serde::{Deserialize, Serialize};
use sqlite::Connection;
use std::sync::Arc;

#[derive(Serialize, Deserialize, Debug)]
struct Book {
    id: Option<i64>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookRequest {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookResponse {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
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

#[tokio::main]
async fn main() {
    // Initialize database
    let db = init_db().await;
    
    // Start the server
    println!("Book API server running on http://localhost:3000");
    axum::Server::bind(&"0.0.0.0:3000".parse().unwrap())
        .serve(app().into_make_service())
        .await
        .unwrap();
}

fn app() -> axum::Router {
    axum::Router::new()
        .route("/health", axum::routing::get(health_check))
        .route("/books", axum::routing::post(create_book))
        .route("/books", axum::routing::get(get_all_books))
        .route("/books/:id", axum::routing::get(get_book))
        .route("/books/:id", axum::routing::put(update_book))
        .route("/books/:id", axum::routing::delete(delete_book))
}

async fn health_check() -> axum::Json<HealthResponse> {
    axum::Json(HealthResponse {
        status: "healthy".to_string(),
    })
}

async fn create_book(
    axum::extract::Json(book_request): axum::extract::Json<BookRequest>,
) -> axum::Json<BookResponse> {
    // Validate required fields
    if book_request.title.trim().is_empty() {
        panic!("Title is required");
    }
    if book_request.author.trim().is_empty() {
        panic!("Author is required");
    }

    // Create book in database
    let db = init_db().await;
    let mut stmt = db.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)").unwrap();
    stmt.bind(1, &book_request.title).unwrap();
    stmt.bind(2, &book_request.author).unwrap();
    stmt.bind(3, book_request.year).unwrap();
    stmt.bind(4, &book_request.isbn).unwrap();
    
    stmt.next().unwrap();
    
    // Get the created book back
    let mut stmt2 = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = last_insert_rowid()").unwrap();
    stmt2.next().unwrap();
    
    let id = stmt2.column_value(0).as_integer().unwrap();
    let title = stmt2.column_value(1).as_text().unwrap();
    let author = stmt2.column_value(2).as_text().unwrap();
    let year = stmt2.column_value(3).as_integer();
    let isbn = stmt2.column_value(4).as_text();
    
    let book = Book {
        id: Some(id),
        title: title.to_string(),
        author: author.to_string(),
        year: year.map(|y| y as i32),
        isbn: isbn.map(|s| s.to_string()),
    };
    
    axum::Json(BookResponse::from(book))
}

async fn get_all_books(
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> axum::Json<Vec<BookResponse>> {
    let db = init_db().await;
    let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books").unwrap();
    
    let mut books = Vec::new();
    while stmt.next().unwrap() {
        let id = stmt.column_value(0).as_integer().unwrap();
        let title = stmt.column_value(1).as_text().unwrap();
        let author = stmt.column_value(2).as_text().unwrap();
        let year = stmt.column_value(3).as_integer();
        let isbn = stmt.column_value(4).as_text();
        
        books.push(BookResponse {
            id,
            title: title.to_string(),
            author: author.to_string(),
            year: year.map(|y| y as i32),
            isbn: isbn.map(|s| s.to_string()),
        });
    }
    
    axum::Json(books)
}

async fn get_book(axum::extract::Path(id): axum::extract::Path<i64>) -> axum::Json<BookResponse> {
    let db = init_db().await;
    let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").unwrap();
    stmt.bind(1, id).unwrap();
    
    stmt.next().unwrap();
    
    let id = stmt.column_value(0).as_integer().unwrap();
    let title = stmt.column_value(1).as_text()..unwrap();
    let author = stmt.column_value(2).as_text().unwrap();
    let year = stmt.column_value(3).as_integer();
    let isbn = stmt.column_value(4).as_text();
    
    axum::Json(BookResponse {
        id,
        title: title.to_string(),
        author: author.to_string(),
        year: year.map(|y| y as i32),
        isbn: isbn.map(|s| s.to_string()),
    })
}

async fn update_book(
    axum::extract::Path(id): axum::extract::Path<i64>,
    axum::extract::Json(book_update): axum::extract::Json<BookRequest>,
) -> axum::Json<BookResponse> {
    let db = init_db().await;
    
    // Validate required fields
    if book_update.title.trim().is_empty() {
        panic!("Title is required");
    }
    if book_update.author.trim().is_empty() {
        panic!("Author is required");
    }

    let mut stmt = db.prepare("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?").unwrap();
    stmt.bind(1, &book_update.title).unwrap();
    stmt.bind(2, &book_update.author).unwrap();
    stmt.bind(3, book_update.year).unwrap();
    stmt.bind(4, &book_update.isbn).unwrap();
    stmt.bind(5, id).unwrap();
    
    stmt.next().unwrap();
    
    // Get the updated book back
    let mut stmt2 = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id=?").unwrap();
    stmt2.bind(1, id).unwrap();
    stmt2.next().unwrap();
    
    let id = stmt2.column_value(0).as_integer().unwrap();
    let title = stmt2.column_value(1).as_text().unwrap();
    let author = stmt2.column_value(2).as_text().unwrap();
    let year = stmt2.column_value(3).as_integer();
    let isbn = stmt2.column_value(4).as_text();
    
    axum::Json(BookResponse {
        id,
        title: title.to_string(),
        author: author.to_string(),
        year: year.map(|y| y as i32),
        isbn: isbn.map(|s| s.to_string()),
    })
}

async fn delete_book(axum::extract::Path(id): axum::extract::Path<i64>) -> axum::Json<bool> {
    let db = init_db().await;
    let mut stmt = db.prepare("DELETE FROM books WHERE id=?").unwrap();
    stmt.bind(1, id).unwrap();
    stmt.next().unwrap();
    
    axum::Json(true)
}

async fn init_db() -> sqlite::Connection {
    let db = sqlite::Connection::open("books.db").unwrap();
    
    // Create books table if it doesn't exist
    db.execute("CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    )").unwrap();
    
    db
}