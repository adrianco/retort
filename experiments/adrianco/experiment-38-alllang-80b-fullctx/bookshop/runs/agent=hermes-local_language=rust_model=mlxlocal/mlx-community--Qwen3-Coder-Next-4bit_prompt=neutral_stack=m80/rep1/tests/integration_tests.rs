use actix_web::{test, App};
use book_api::{configure_routes, health, start_server};
use sqlx::Connection;

// Helper function to create a fresh database connection for each test
async fn get_test_db() -> sqlx::Pool<sqlx::Sqlite> {
    // Use an in-memory database for each test
    let database_url = "sqlite::memory:";
    let pool = sqlx::sqlite::SqlitePoolOptions::new()
        .max_connections(1)
        .connect(database_url)
        .await
        .expect("Failed to connect to in-memory database");
    
    // Create the books table
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL UNIQUE
        )
        "#,
    )
    .execute(&pool)
    .await
    .expect("Failed to create test table");
    
    pool
}

#[actix_web::test]
async fn test_health_endpoint() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;
    
    assert_eq!(resp.status(), 200);
}

#[actix_web::test]
async fn test_create_book() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(serde_json::json!({
            "title": "Test Book",
            "author": "Test Author",
            "year": 2024,
            "isbn": "1234567890"
        }))
        .to_request();
    let resp = test::call_service(&app, req).await;
    
    assert_eq!(resp.status(), 201);
}

#[actix_web::test]
async fn test_get_books() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;
    
    assert_eq!(resp.status(), 200);
}

#[actix_web::test]
async fn test_get_book_by_id() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    // First create a book
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(serde_json::json!({
            "title": "Get By Id Book",
            "author": "Author Name",
            "year": 2024,
            "isbn": "0987654321"
        }))
        .to_request();
    let create_resp = test::call_service(&app, create_req).await;
    assert_eq!(create_resp.status(), 201);
    
    // Now get the book by ID
    let get_req = test::TestRequest::get().uri("/books/1").to_request();
    let get_resp = test::call_service(&app, get_req).await;
    
    assert_eq!(get_resp.status(), 200);
}

#[actix_web::test]
async fn test_update_book() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    // First create a book
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(serde_json::json!({
            "title": "Original Title",
            "author": "Original Author",
            "year": 2020,
            "isbn": "1111111111"
        }))
        .to_request();
    let create_resp = test::call_service(&app, create_req).await;
    assert_eq!(create_resp.status(), 201);
    
    // Update the book
    let update_req = test::TestRequest::put()
        .uri("/books/1")
        .set_json(serde_json::json!({
            "title": "Updated Title",
            "author": "Updated Author"
        }))
        .to_request();
    let update_resp = test::call_service(&app, update_req).await;
    
    assert_eq!(update_resp.status(), 200);
}

#[actix_web::test]
async fn test_delete_book() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    // First create a book
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(serde_json::json!({
            "title": "To Delete",
            "author": "Delete Author",
            "year": 2024,
            "isbn": "2222222222"
        }))
        .to_request();
    let create_resp = test::call_service(&app, create_req).await;
    assert_eq!(create_resp.status(), 201);
    
    // Delete the book
    let delete_req = test::TestRequest::delete().uri("/books/1").to_request();
    let delete_resp = test::call_service(&app, delete_req).await;
    
    assert_eq!(delete_resp.status(), 204);
}

#[actix_web::test]
async fn test_get_books_by_author_filter() {
    let pool = get_test_db().await;
    
    let app = App::new()
        .app_data(actix_web::web::Data::new(book_api::AppState { pool }))
        .configure(configure_routes);
    let app = test::init_service(app).await;
    
    // Create some books with the same author
    for i in 0..3 {
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(serde_json::json!({
                "title": format!("Book {}", i),
                "author": "Filter Author",
                "year": 2024,
                "isbn": format!("333333333{}", i)
            }))
            .to_request();
        let _resp = test::call_service(&app, create_req).await;
    }
    
    // Filter by author
    let filter_req = test::TestRequest::get()
        .uri("/books?author=Filter%20Author")
        .to_request();
    let filter_resp = test::call_service(&app, filter_req).await;
    
    assert_eq!(filter_resp.status(), 200);
}
