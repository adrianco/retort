use actix_web::{web, App, HttpServer, HttpResponse, Result, Responder, get, post, put, delete};
use serde_json::json;
use sqlx::SqlitePool;

mod models;
mod database;

use models::{Book, BookInput, HealthResponse};
use database::Database;

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(HealthResponse {
        status: "OK".to_string(),
    })
}

#[post("/books")]
async fn create_book(db: web::Data<SqlitePool>, book_input: web::Json<BookInput>) -> Result<HttpResponse> {
    // Validate input
    if book_input.title.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(json!({
            "error": "Title is required"
        })));
    }
    
    if book_input.author.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(json!({
            "error": "Author is required"
        })));
    }

    let book = Book::from(book_input.into_inner());
    
    // Create the book in database
    let db_instance = Database::new("sqlite://books.db").await;
    let db_instance = match db_instance {
        Ok(db) => db,
        Err(e) => {
            eprintln!("Failed to initialize database: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to initialize database",
                "details": e.to_string()
            })));
        }
    };
    
    let created_book = db_instance.create_book(&book).await;
    let created_book = match created_book {
        Ok(book) => book,
        Err(e) => {
            eprintln!("Failed to create book: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to create book",
                "details": e.to_string()
            })));
        }
    };

    Ok(HttpResponse::Created().json(created_book))
}

#[get("/books")]
async fn get_books(db: web::Data<SqlitePool>, author: web::Query<Option<String>>) -> Result<HttpResponse> {
    let db_instance = Database::new("sqlite://books.db").await;
    let db_instance = match db_instance {
        Ok(db) => db,
        Err(e) => {
            eprintln!("Failed to initialize database: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to initialize database",
                "details": e.to_string()
            })));
        }
    };
    
    let books = db_instance.get_books(author.as_ref().map(|s| s.as_str())).await;
    let books = match books {
        Ok(books) => books,
        Err(e) => {
            eprintln!("Failed to fetch books: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to fetch books",
                "details": e.to_string()
            })));
        }
    };

    Ok(HttpResponse::Ok().json(books))
}

#[get("/books/{id}")]
async fn get_book(db: web::Data<SqlitePool>, id: web::Path<i32>) -> Result<HttpResponse> {
    let db_instance = Database::new("sqlite://books.db").await;
    let db_instance = match db_instance {
        Ok(db) => db,
        Err(e) => {
            eprintln!("Failed to initialize database: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to initialize database",
                "details": e.to_string()
            })));
        }
    };
    
    let book = db_instance.get_book(id.into_inner()).await;
    let book = match book {
        Ok(book) => book,
        Err(e) => {
            eprintln!("Failed to fetch book: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to fetch book",
                "details": e.to_string()
            })));
        }
    };

    match book {
        Some(book) => Ok(HttpResponse::Ok().json(book)),
        None => Ok(HttpResponse::NotFound().json(json!({
            "error": "Book not found"
        }))),
    }
}

#[put("/books/{id}")]
async fn update_book(db: web::Data<SqlitePool>, id: web::Path<i32>, book_input: web::Json<BookInput>) -> Result<HttpResponse> {
    // Validate input
    if book_input.title.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(json!({
            "error": "Title is required"
        })));
    }
    
    if book_input.author.trim().is_empty() {
        return Ok(HttpResponse::BadRequest().json(json!({
            "error": "Author is required"
        })));
    }

    let book_id = id.into_inner();
    let book = Book::from(book_input.into_inner());

    let db_instance = Database::new("sqlite://books.db").await;
    let db_instance = match db_instance {
        Ok(db) => db,
        Err(e) => {
            eprintln!("Failed to initialize database: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to initialize database",
                "details": e.to_string()
            })));
        }
    };
    
    let updated_book = db_instance.update_book(book_id, &book).await;
    let updated_book = match updated_book {
        Ok(book) => book,
        Err(e) => {
            eprintln!("Failed to update book: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to update book",
                "details": e.to_string()
            })));
        }
    };

    match updated_book {
        Some(book) => Ok(HttpResponse::Ok().json(book)),
        None => Ok(HttpResponse::NotFound().json(json!({
            "error": "Book not found"
        }))),
    }
}

#[delete("/books/{id}")]
async fn delete_book(db: web::Data<SqlitePool>, id: web::Path<i32>) -> Result<HttpResponse> {
    let db_instance = Database::new("sqlite://books.db").await;
    let db_instance = match db_instance {
        Ok(db) => db,
        Err(e) => {
            eprintln!("Failed to initialize database: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to initialize database",
                "details": e.to_string()
            })));
        }
    };
    
    let deleted = db_instance.delete_book(id.into_inner()).await;
    let deleted = match deleted {
        Ok(deleted) => deleted,
        Err(e) => {
            eprintln!("Failed to delete book: {}", e);
            return Ok(HttpResponse::InternalServerError().json(json!({
                "error": "Failed to delete book",
                "details": e.to_string()
            })));
        }
    };

    if deleted {
        Ok(HttpResponse::Ok().json(json!({
            "message": "Book deleted successfully"
        })))
    } else {
        Ok(HttpResponse::NotFound().json(json!({
            "error": "Book not found"
        })))
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize the database
    let db_url = "sqlite://books.db";
    let pool = SqlitePool::connect(db_url).await;
    let pool = match pool {
        Ok(pool) => pool,
        Err(e) => {
            eprintln!("Failed to connect to database: {}", e);
            std::process::exit(1);
        }
    };
    
    // Create database instance to initialize schema
    let db = Database::new(db_url).await;
    let db = match db {
        Ok(db) => db,
        Err(e) => {
            eprintln!("Failed to initialize database: {}", e);
            std::process::exit(1);
        }
    };

    println!("Starting server on http://127.0.0.1:8080");
    
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