mod db;
mod handlers;
mod models;
mod schema;

use actix_web::{web, App, HttpServer};
use db::{AppState, run_migrations};
use handlers::configure_services;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Run migrations
    run_migrations().expect("Failed to run migrations");

    println!("Starting server on http://127.0.0.1:8080");

    let app_state = AppState::new();

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(app_state.clone()))
            .configure(configure_services)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}

#[cfg(test)]
mod tests {
    use actix_web::{web};
    use std::fs;

    use crate::db::{AppState, run_migrations};
    use crate::handlers::{health, list_books, create_book};
    use crate::models::{CreateBookRequest, ListBooksQuery};

    #[test]
    fn test_model_structs() {
        // Test that all model structs compile
        let book = crate::models::Book {
            id: 1,
            title: "Test".to_string(),
            author: "Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };
        assert_eq!(book.title, "Test");
        assert_eq!(book.author, "Author");

        let new_book = crate::models::NewBook {
            title: "New".to_string(),
            author: "New Author".to_string(),
            year: 2024,
            isbn: "0987654321".to_string(),
        };
        assert_eq!(new_book.title, "New");

        let create_request = CreateBookRequest {
            title: "Title".to_string(),
            author: "Author".to_string(),
            year: 2024,
            isbn: "1111111111".to_string(),
        };
        assert_eq!(create_request.title, "Title");

        let update_request = crate::models::UpdateBookRequest {
            title: Some("Updated".to_string()),
            author: None,
            year: None,
            isbn: None,
        };
        assert_eq!(update_request.title, Some("Updated".to_string()));

        let list_query = ListBooksQuery {
            author: Some("Author".to_string()),
        };
        assert_eq!(list_query.author, Some("Author".to_string()));
    }

    #[test]
    fn test_state_clone() {
        let state = AppState::new();
        let _ = state.clone();
    }

    #[actix_web::test]
    async fn test_health_endpoint() {
        let result = health().await;
        assert_eq!(result.status(), actix_web::http::StatusCode::OK);
    }

    #[actix_web::test]
    async fn test_create_and_list_books() {
        // Use a temporary database for testing
        let test_db = "test_books.db";
        fs::remove_file(test_db).ok();

        // Set the DATABASE_URL before anything else - THIS MUST BE BEFORE run_migrations
        std::env::set_var("DATABASE_URL", test_db);
        
        // Run migrations and print the result
        let result = run_migrations();
        println!("Migration result: {:?}", result);
        result.expect("Failed to run migrations");

        let app_state = AppState::new();

        // Create a book
        let create_request = CreateBookRequest {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };

        let body = web::Json(create_request);
        let result = create_book(body, web::Data::new(app_state.clone())).await;
        
        // Print the error for debugging
        if let Err(e) = &result {
            eprintln!("Create book error: {:?}", e);
        }
        
        let response = result.unwrap();
        assert_eq!(response.status(), actix_web::http::StatusCode::CREATED);

        // List books
        let query = web::Query(ListBooksQuery { author: None });
        let result = list_books(query, web::Data::new(app_state)).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap().status(), actix_web::http::StatusCode::OK);
    }

    #[actix_web::test]
    async fn test_validation_errors() {
        let app_state = AppState::new();

        // Test missing title
        let create_request = CreateBookRequest {
            title: "".to_string(),
            author: "Test Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };

        let body = web::Json(create_request);
        let result = create_book(body, web::Data::new(app_state)).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap().status(), actix_web::http::StatusCode::BAD_REQUEST);
    }
}
