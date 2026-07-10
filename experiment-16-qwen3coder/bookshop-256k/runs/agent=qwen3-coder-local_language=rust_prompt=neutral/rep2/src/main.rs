use actix_web::{web, App, HttpServer, HttpResponse, Result, middleware::Logger, http::StatusCode};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Serialize, Deserialize)]
struct BookCreate {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Serialize, Deserialize)]
struct BookUpdate {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

// In-memory storage for books
lazy_static::lazy_static! {
    static ref BOOKS: Mutex<Vec<Book>> = Mutex::new(Vec::new());
    static ref NEXT_ID: Mutex<u32> = Mutex::new(1);
}

async fn health() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(HealthResponse { status: "OK".to_string() }))
}

async fn create_book(book: web::Json<BookCreate>) -> Result<HttpResponse> {
    // Validate required fields
    if book.title.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json("Title is required"));
    }
    
    if book.author.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json("Author is required"));
    }

    // Generate a new ID
    let id = {
        let mut next_id = NEXT_ID.lock().unwrap();
        let id = format!("book-{}", *next_id);
        *next_id += 1;
        id
    };

    let new_book = Book {
        id: id.clone(),
        title: book.title.clone(),
        author: book.author.clone(),
        year: book.year,
        isbn: book.isbn.clone(),
    };

    BOOKS.lock().unwrap().push(new_book.clone());

    Ok(HttpResponse::Created().json(new_book))
}

async fn get_books(query: web::Query<HashMap<String, String>>) -> Result<HttpResponse> {
    let books = {
        let books = BOOKS.lock().unwrap();
        let mut filtered = books.clone();
        
        if let Some(author) = query.get("author") {
            filtered.retain(|book| book.author.contains(author));
        }
        
        filtered
    };

    Ok(HttpResponse::Ok().json(books))
}

async fn get_book(path: web::Path<String>) -> Result<HttpResponse> {
    let id = path.into_inner();
    
    let books = BOOKS.lock().unwrap();
    if let Some(book) = books.iter().find(|book| book.id == id) {
        Ok(HttpResponse::Ok().json(book.clone()))
    } else {
        Ok(HttpResponse::NotFound().json("Book not found"))
    }
}

async fn update_book(
    path: web::Path<String>,
    book_data: web::Json<BookUpdate>
) -> Result<HttpResponse> {
    let id = path.into_inner();
    
    let mut books = BOOKS.lock().unwrap();
    
    if let Some(book) = books.iter_mut().find(|book| book.id == id) {
        // Update the book fields if provided
        if let Some(title) = &book_data.title {
            book.title = title.clone();
        }
        if let Some(author) = &book_data.author {
            book.author = author.clone();
        }
        if let Some(year) = book_data.year {
            book.year = year;
        }
        if let Some(isbn) = &book_data.isbn {
            book.isbn = isbn.clone();
        }
        
        Ok(HttpResponse::Ok().json(book.clone()))
    } else {
        Ok(HttpResponse::NotFound().json("Book not found"))
    }
}

async fn delete_book(path: web::Path<String>) -> Result<HttpResponse> {
    let id = path.into_inner();
    
    let mut books = BOOKS.lock().unwrap();
    let initial_len = books.len();
    books.retain(|book| book.id != id);
    
    if books.len() == initial_len {
        Ok(HttpResponse::NotFound().json("Book not found"))
    } else {
        Ok(HttpResponse::NoContent().finish())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::test;
    use actix_web::http::StatusCode;
    
    #[actix_web::test]
    async fn test_health_endpoint() {
        let app = test::init_service(
            App::new()
                .route("/health", web::get().to(health))
        ).await;
        
        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;
        
        assert_eq!(resp.status(), StatusCode::OK);
    }
    
    #[actix_web::test]
    async fn test_create_and_get_book() {
        let app = test::init_service(
            App::new()
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book))
        ).await;
        
        // Create a book
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(BookCreate {
                title: "Test Book".to_string(),
                author: "Test Author".to_string(),
                year: 2023,
                isbn: "1234567890".to_string(),
            })
            .to_request();
            
        let create_resp = test::call_service(&app, create_req).await;
        assert_eq!(create_resp.status(), StatusCode::CREATED);
        
        // Extract the book ID from the response
        let body = test::read_body(create_resp).await;
        let book: Book = serde_json::from_slice(&body).unwrap();
        
        // Get the book by ID
        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book.id))
            .to_request();
            
        let get_resp = test::call_service(&app, get_req).await;
        assert_eq!(get_resp.status(), StatusCode::OK);
    }
    
    #[actix_web::test]
    async fn test_list_books() {
        let app = test::init_service(
            App::new()
                .route("/books", web::get().to(get_books))
        ).await;
        
        let req = test::TestRequest::get().uri("/books").to_request();
        let resp = test::call_service(&app, req).await;
        
        assert_eq!(resp.status(), StatusCode::OK);
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    HttpServer::new(|| {
        App::new()
            .wrap(Logger::default())
            .route("/health", web::get().to(health))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}