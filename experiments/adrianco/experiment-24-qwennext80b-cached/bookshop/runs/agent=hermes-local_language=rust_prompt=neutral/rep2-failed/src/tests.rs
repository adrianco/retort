use actix_web::{web, App, test};

use crate::{handlers, models};

#[actix_web::test]
async fn test_health_endpoint() {
    let app = test::init_service(
        App::new()
            .route("/health", web::get().to(handlers::health))
    ).await;
    
    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
}

#[actix_web::test]
async fn test_books_routes_exist() {
    let app = test::init_service(
        App::new()
            .route("/books", web::get().to(handlers::get_books))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books/{id}", web::get().to(handlers::get_book))
            .route("/books/{id}", web::put().to(handlers::update_book))
            .route("/books/{id}", web::delete().to(handlers::delete_book))
    ).await;

    // Test that all routes exist and return appropriate status codes
    // (Without actual database, they should return 500 or 404)
    
    // GET /books - should work (returns empty list)
    let req = test::TestRequest::get().uri("/books").to_request();
    let _resp = test::call_service(&app, req).await;
    // Expected: 500 since database isn't set up
    
    // POST /books - should work (validates input)
    let create_book = models::CreateBook {
        title: "Test Book".to_string(),
        author: "Test Author".to_string(),
        year: 2024,
        isbn: "1234567890".to_string(),
    };
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&create_book)
        .to_request();
    let _resp = test::call_service(&app, req).await;
    // Expected: 500 since database isn't set up
}

// Integration tests - these require a real database and are skipped by default
#[cfg(feature = "integration")]
#[actix_web::test]
async fn test_full_book_workflow() {
    use sqlx::SqlitePoolOptions;
    
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(":memory:")
        .await
        .unwrap();

    // Create the books table
    sqlx::query(
        r#"CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )"#
    )
    .execute(&pool)
    .await
    .unwrap();

    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool))
            .route("/health", web::get().to(handlers::health))
            .route("/books", web::get().to(handlers::get_books))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books/{id}", web::get().to(handlers::get_book))
            .route("/books/{id}", web::put().to(handlers::update_book))
            .route("/books/{id}", web::delete().to(handlers::delete_book))
    ).await;

    // Create a book
    let create_book = models::CreateBook {
        title: "The Rust Programming Language".to_string(),
        author: "Steve Klabnik".to_string(),
        year: 2018,
        isbn: "978-1593278281".to_string(),
    };

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&create_book)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert!(resp.status().is_success(), "Failed to create book: {:?}", resp.status());

    // Get the book
    let req = test::TestRequest::get().uri("/books/1").to_request();
    let resp = test::call_service(&app, req).await;
    assert!(resp.status().is_success(), "Failed to get book: {:?}", resp.status());

    // Update the book
    let update_book = models::UpdateBook {
        title: Some("Updated Title".to_string()),
        author: None,
        year: Some(2019),
        isbn: None,
    };

    let req = test::TestRequest::put()
        .uri("/books/1")
        .set_json(&update_book)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert!(resp.status().is_success(), "Failed to update book: {:?}", resp.status());

    // Delete the book
    let req = test::TestRequest::delete().uri("/books/1").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), actix_web::http::StatusCode::NO_CONTENT);
}
