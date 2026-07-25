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
    use crate::db::AppState;
    use crate::models::{Book, NewBook, CreateBookRequest, UpdateBookRequest, ListBooksQuery};

    #[test]
    fn test_model_structs() {
        // Test that all model structs compile
        let book = Book {
            id: 1,
            title: "Test".to_string(),
            author: "Author".to_string(),
            year: 2024,
            isbn: "1234567890".to_string(),
        };
        assert_eq!(book.title, "Test");
        assert_eq!(book.author, "Author");

        let new_book = NewBook {
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

        let update_request = UpdateBookRequest {
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
}
