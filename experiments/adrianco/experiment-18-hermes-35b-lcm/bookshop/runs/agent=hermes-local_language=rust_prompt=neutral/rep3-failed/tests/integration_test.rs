use actix_web::test;
use book_api::db::Database;

fn setup_db() -> actix_web::web::Data<Database> {
    actix_web::web::Data::new(
        Database::new(":memory:").expect("Failed to create test database")
    )
}

fn build_app() -> actix_web::App {
    let db = setup_db();
    let cors = actix_cors::Cors::default().allow_any_origin();
    actix_web::App::new()
        .app_data(db)
        .wrap(cors)
        .route("/health", actix_web::web::get().to(book_api::routes::health_check))
        .route("/books", actix_web::web::post().to(book_api::routes::create_book))
        .route("/books", actix_web::web::get().to(book_api::routes::list_books))
        .route("/books/{id}", actix_web::web::get().to(book_api::routes::get_book))
        .route("/books/{id}", actix_web::web::put().to(book_api::routes::update_book))
        .route("/books/{id}", actix_web::web::delete().to(book_api::routes::delete_book))
}

async fn init_app() -> actix_web::dev::AppService {
    let app = build_app();
    test::init_service(app).await
}

// ============================================================
// Create book tests
// ============================================================

#[tokio::test]
async fn test_create_book() {
    let app = init_app().await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    let body_bytes = test::read_body(resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body["title"], "The Great Gatsby");
    assert_eq!(body["author"], "F. Scott Fitzgerald");
    assert_eq!(body["year"].as_i64(), Some(1925));
    assert_eq!(body["isbn"], "978-0743273565");
    assert!(!body["id"].is_null());
}

#[tokio::test]
async fn test_create_book_validation_missing_title() {
    let app = init_app().await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "author": "Some Author",
            "year": 2000
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let body_bytes = test::read_body(resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body["error"], "Title and author are required");
}

#[tokio::test]
async fn test_create_book_validation_missing_author() {
    let app = init_app().await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "title": "Some Title",
            "year": 2000
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);
}

#[tokio::test]
async fn test_create_book_validation_empty_fields() {
    let app = init_app().await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "title": "   ",
            "author": "Author"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "title": "Title",
            "author": "   "
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);
}

#[tokio::test]
async fn test_create_book_no_optional_fields() {
    let app = init_app().await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "title": "Minimal Book",
            "author": "Minimal Author"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    let body_bytes = test::read_body(resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body["title"], "Minimal Book");
    assert!(body["year"].is_null());
    assert!(body["isbn"].is_null());
}

// ============================================================
// List books tests
// ============================================================

#[tokio::test]
async fn test_list_books_empty() {
    let app = init_app().await;

    let req = test::TestRequest::get()
        .uri("/books")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let body: Vec<serde_json::Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body.len(), 0);
}

#[tokio::test]
async fn test_list_books_multiple() {
    let app = init_app().await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book A",
                "author": "John Smith",
                "year": 2020,
                "isbn": "isbn-001"
            }))
            .to_request(),
    ).await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book B",
                "author": "Jane Doe",
                "year": 2021,
                "isbn": "isbn-002"
            }))
            .to_request(),
    ).await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book C",
                "author": "John Smith Jr",
                "year": 2022
            }))
            .to_request(),
    ).await;

    let req = test::TestRequest::get()
        .uri("/books")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 3);
}

#[tokio::test]
async fn test_list_books_filter_by_author() {
    let app = init_app().await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book A",
                "author": "John Smith",
                "year": 2020
            }))
            .to_request(),
    ).await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book B",
                "author": "Jane Doe",
                "year": 2021
            }))
            .to_request(),
    ).await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book C",
                "author": "John Smith Jr",
                "year": 2022
            }))
            .to_request(),
    ).await;

    let req = test::TestRequest::get()
        .uri("/books?author=John")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| {
        let author = b["author"].as_str().unwrap();
        author.contains("John")
    }));
}

// ============================================================
// Get book tests
// ============================================================

#[tokio::test]
async fn test_get_book() {
    let app = init_app().await;

    let create_resp = test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "isbn": "isbn-003"
            }))
            .to_request(),
    ).await;

    let body_bytes = test::read_body(create_resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    let id = body["id"].as_str().unwrap();

    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", id))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let book: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book["id"], id);
    assert_eq!(book["title"], "1984");
    assert_eq!(book["author"], "George Orwell");
    assert_eq!(book["year"].as_i64(), Some(1949));
}

#[tokio::test]
async fn test_get_book_not_found() {
    let app = init_app().await;

    let req = test::TestRequest::get()
        .uri("/books/non-existent-id")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);

    let body_bytes = test::read_body(resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body["error"], "Book not found");
}

// ============================================================
// Update book tests
// ============================================================

#[tokio::test]
async fn test_update_book() {
    let app = init_app().await;

    let create_resp = test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Original Title",
                "author": "Original Author",
                "year": 2000,
                "isbn": "isbn-004"
            }))
            .to_request(),
    ).await;

    let body_bytes = test::read_body(create_resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    let id = body["id"].as_str().unwrap();

    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", id))
        .json(&serde_json::json!({
            "title": "Updated Title"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let book: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book["title"], "Updated Title");
    assert_eq!(book["author"], "Original Author");
    assert_eq!(book["year"].as_i64(), Some(2000));
}

#[tokio::test]
async fn test_update_all_fields() {
    let app = init_app().await;

    let create_resp = test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Old Title",
                "author": "Old Author"
            }))
            .to_request(),
    ).await;

    let body_bytes = test::read_body(create_resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    let id = body["id"].as_str().unwrap();

    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", id))
        .json(&serde_json::json!({
            "title": "New Title",
            "author": "New Author",
            "year": 2023,
            "isbn": "isbn-999"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let book: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book["title"], "New Title");
    assert_eq!(book["author"], "New Author");
    assert_eq!(book["year"].as_i64(), Some(2023));
    assert_eq!(book["isbn"], "isbn-999");
}

#[tokio::test]
async fn test_update_nonexistent_book() {
    let app = init_app().await;

    let req = test::TestRequest::put()
        .uri("/books/non-existent-id")
        .json(&serde_json::json!({
            "title": "New Title"
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}

// ============================================================
// Delete book tests
// ============================================================

#[tokio::test]
async fn test_delete_book() {
    let app = init_app().await;

    let create_resp = test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "To Delete",
                "author": "Author"
            }))
            .to_request(),
    ).await;

    let body_bytes = test::read_body(create_resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    let id = body["id"].as_str().unwrap();

    let req = test::TestRequest::delete()
        .uri(&format!("/books/{}", id))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 204);

    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", id))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}

#[tokio::test]
async fn test_delete_book_not_found() {
    let app = init_app().await;

    let req = test::TestRequest::delete()
        .uri("/books/non-existent")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}

// ============================================================
// Health check test
// ============================================================

#[tokio::test]
async fn test_health_check() {
    let app = init_app().await;

    let req = test::TestRequest::get()
        .uri("/health")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body["status"], "healthy");
}

// ============================================================
// Full workflow test
// ============================================================

#[tokio::test]
async fn test_full_workflow() {
    let app = init_app().await;

    // Create
    let create_resp = test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Rust Programming",
                "author": "Alex Smith",
                "year": 2023,
                "isbn": "isbn-rust"
            }))
            .to_request(),
    ).await;
    assert_eq!(create_resp.status(), 201);

    let body_bytes = test::read_body(create_resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    let id = body["id"].as_str().unwrap();

    // List
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let body_bytes = test::read_body(resp).await;
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 1);

    // Get
    let req = test::TestRequest::get().uri(&format!("/books/{}", id)).to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    // Update
    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", id))
        .json(&serde_json::json!({
            "year": 2024
        }))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    // Delete
    let req = test::TestRequest::delete().uri(&format!("/books/{}", id)).to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 204);

    // Verify deleted
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let body_bytes = test::read_body(resp).await;
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 0);
}

// ============================================================
// Additional validation tests
// ============================================================

#[tokio::test]
async fn test_create_book_validation_both_fields_empty() {
    let app = init_app().await;

    let req = test::TestRequest::post()
        .uri("/books")
        .json(&serde_json::json!({
            "title": "   ",
            "author": "   "
        }))
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let body_bytes = test::read_body(resp).await;
    let body: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(body["error"], "Title and author are required");
}

#[tokio::test]
async fn test_list_books_contains_field() {
    let app = init_app().await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book 1",
                "author": "John Smith"
            }))
            .to_request(),
    ).await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book 2",
                "author": "Jane Smithson"
            }))
            .to_request(),
    ).await;

    test::call_service(
        &app,
        test::TestRequest::post()
            .uri("/books")
            .json(&serde_json::json!({
                "title": "Book 3",
                "author": "Bob Jones"
            }))
            .to_request(),
    ).await;

    let req = test::TestRequest::get()
        .uri("/books?author=smith")
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body_bytes = test::read_body(resp).await;
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 2);
}
