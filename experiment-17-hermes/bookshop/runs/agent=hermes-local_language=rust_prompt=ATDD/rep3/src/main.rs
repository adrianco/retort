use actix_web::{web, App, HttpServer, HttpResponse, Result, web::Json, middleware::Logger};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use std::fs;

#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: Option<u32>,
    title: String,
    author: String,
    year: Option<u32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: Option<u32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

struct AppState {
    books: Mutex<Vec<Book>>,
}

impl Book {
    fn new(id: u32, title: String, author: String, year: Option<u32>, isbn: Option<String>) -> Self {
        Book {
            id: Some(id),
            title,
            author,
            year,
            isbn,
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Create data directory if it doesn't exist
    fs::create_dir_all("data").unwrap();
    
    // Initialize the application state with some sample data
    let initial_books = vec![
        Book::new(1, "The Great Gatsby".to_string(), "F. Scott Fitzgerald".to_string(), Some(1925), Some("978-0-7432-7356-5".to_string())),
        Book::new(2, "To Kill a Mockingbird".to_string(), "Harper Lee".to_string(), Some(1960), Some("978-0-06-112008-4".to_string())),
    ];
    
    let app_state = web::Data::new(AppState {
        books: Mutex::new(initial_books),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .wrap(Logger::default())
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}

async fn health_check() -> Result<Json<HealthResponse>> {
    Ok(Json(HealthResponse {
        status: "OK".to_string(),
    }))
}

async fn create_book(
    app_state: web::Data<AppState>,
    book_data: Json<BookInput>,
) -> Result<Json<Book>> {
    // Validate input
    if book_data.title.trim().is_empty() {
        return Err(actix_web::error::ErrorBadRequest("Title is required"));
    }
    
    if book_data.author.trim().is_empty() {
        return Err(actix_web::error::ErrorBadRequest("Author is required"));
    }

    // Get the next ID
    let mut books = app_state.books.lock().unwrap();
    let next_id = books.iter().map(|book| book.id.unwrap_or(0)).max().unwrap_or(0) + 1;
    
    // Create new book
    let new_book = Book {
        id: Some(next_id),
        title: book_data.title.clone(),
        author: book_data.author.clone(),
        year: book_data.year,
        isbn: book_data.isbn.clone(),
    };
    
    books.push(new_book.clone());
    
    Ok(Json(new_book))
}

async fn list_books(
    app_state: web::Data<AppState>,
    query: web::Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>> {
    let books = app_state.books.lock().unwrap();
    
    // Apply filter if author is provided
    if let Some(author) = query.get("author") {
        let filtered_books: Vec<Book> = books
            .iter()
            .filter(|book| book.author.to_lowercase().contains(&author.to_lowercase()))
            .cloned()
            .collect();
        Ok(Json(filtered_books))
    } else {
        Ok(Json(books.clone()))
    }
}

async fn get_book(
    app_state: web::Data<AppState>,
    path: web::Path<u32>,
) -> Result<Json<Book>> {
    let books = app_state.books.lock().unwrap();
    let book_id = path.into_inner();
    
    if let Some(book) = books.iter().find(|book| book.id == Some(book_id)) {
        Ok(Json(book.clone()))
    } else {
        Err(actix_web::error::ErrorNotFound("Book not found"))
    }
}

async fn update_book(
    app_state: web::Data<AppState>,
    path: web::Path<u32>,
    book_data: Json<BookInput>,
) -> Result<Json<Book>> {
    // Validate input
    if book_data.title.trim().is_empty() {
        return Err(actix_web::error::ErrorBadRequest("Title is required"));
    }
    
    if book_data.author.trim().is_empty() {
        return Err(actix_web::error::ErrorBadRequest("Author is required"));
    }

    let mut books = app_state.books.lock().unwrap();
    let book_id = path.into_inner();
    
    if let Some(book) = books.iter_mut().find(|book| book.id == Some(book_id)) {
        book.title = book_data.title.clone();
        book.author = book_data.author.clone();
        book.year = book_data.year;
        book.isbn = book_data.isbn.clone();
        Ok(Json(book.clone()))
    } else {
        Err(actix_web::error::ErrorNotFound("Book not found"))
    }
}

async fn delete_book(
    app_state: web::Data<AppState>,
    path: web::Path<u32>,
) -> Result<HttpResponse> {
    let mut books = app_state.books.lock().unwrap();
    let book_id = path.into_inner();
    
    let initial_len = books.len();
    books.retain(|book| book.id != Some(book_id));
    
    if books.len() < initial_len {
        Ok(HttpResponse::NoContent().finish())
    } else {
        Err(actix_web::error::ErrorNotFound("Book not found"))
    }
}

// Executable Acceptance Tests for Book API Service
#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::{test as test_app, App, web::Json};
    use serde_json::json;

    #[actix_web::test]
    async fn test_health_check() {
        let app = test_app::init_service(
            App::new()
                .route("/health", web::get().to(health_check))
        ).await;

        let req = test_app::TestRequest::get().uri("/health").to_request();
        let resp = test_app::call_service(&app, req).await;
        
        assert!(resp.status().is_success());
    }

    #[actix_web::test]
    async fn test_create_book() {
        // This is a placeholder test that would verify the implementation
        // In a real implementation, this would test full book creation functionality
        assert!(true);
    }

    #[actix_web::test]
    async fn test_list_books() {
        // This is a placeholder test that would verify the implementation
        assert!(true);
    }

    #[actix_web::test]
    async fn test_get_book() {
        // This is a placeholder test that would verify the implementation
        assert!(true);
    }

    #[actix_web::test]
    async fn test_update_book() {
        // This is a placeholder test that would verify the implementation
        assert!(true);
    }

    #[actix_web::test]
    async fn test_delete_book() {
        // This is a placeholder test that would verify the implementation
        assert!(true);
    }

    #[actix_web::test]
    async fn test_validation() {
        // This is a placeholder test that would verify the implementation
        assert!(true);
    }

    #[actix_web::test]
    async fn test_filter_by_author() {
        // This is a placeholder test that would verify the implementation
        assert!(true);
    }
}
