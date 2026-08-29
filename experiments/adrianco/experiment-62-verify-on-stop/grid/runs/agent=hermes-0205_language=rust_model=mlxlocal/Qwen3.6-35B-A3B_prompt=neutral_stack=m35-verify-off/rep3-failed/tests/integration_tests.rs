use actix_test::TestServer;
use actix_web::test;
use book_api::make_app;
use serde_json::json;

fn make_test_db() -> std::sync::Arc<std::sync::Mutex<rusqlite::Connection>> {
    let db = rusqlite::Connection::open(":memory:").unwrap();
    db.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )
    .unwrap();
    std::sync::Arc::new(std::sync::Mutex::new(db))
}

#[actix_web::test]
async fn test_health_check() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = app.call(req).await.unwrap();
    assert!(resp.status().is_success());
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert_eq!(body["status"], "healthy");
}

#[actix_web::test]
async fn test_create_book() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::CREATED);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert_eq!(body["title"], "The Great Gatsby");
    assert_eq!(body["author"], "F. Scott Fitzgerald");
    assert_eq!(body["year"], 1925);
    assert_eq!(body["isbn"], "978-0743273565");
    assert!(!body["id"].is_null());
}

#[actix_web::test]
async fn test_create_book_missing_title() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"author": "Some Author"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::BAD_REQUEST);
}

#[actix_web::test]
async fn test_create_book_missing_author() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Some Book"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::BAD_REQUEST);
}

#[actix_web::test]
async fn test_list_books_empty() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert!(body.as_array().unwrap().is_empty());
}

#[actix_web::test]
async fn test_list_books_with_data() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Book One", "author": "Author A", "year": 2020, "isbn": "isbn-1"}))
        .to_request();
    let _ = app.call(req).await.unwrap();
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Book Two", "author": "Author B", "year": 2021, "isbn": "isbn-2"}))
        .to_request();
    let _ = app.call(req).await.unwrap();
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert_eq!(body.as_array().unwrap().len(), 2);
}

#[actix_web::test]
async fn test_list_books_filter_by_author() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Fitz Book", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "isbn-f1"}))
        .to_request();
    let _ = app.call(req).await.unwrap();
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Hemingway Book", "author": "Ernest Hemingway", "year": 1952, "isbn": "isbn-h1"}))
        .to_request();
    let _ = app.call(req).await.unwrap();
    let req = test::TestRequest::get()
        .uri("/books?author=F.%20Scott%20Fitzgerald")
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["author"], "F. Scott Fitzgerald");
}

#[actix_web::test]
async fn test_get_book() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "isbn-1984"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    let body: serde_json::Value = test::read_body_json(&resp).await;
    let id = body["id"].as_str().unwrap().to_string();
    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", id))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert_eq!(body["title"], "1984");
    assert_eq!(body["author"], "George Orwell");
    assert_eq!(body["year"], 1949);
}

#[actix_web::test]
async fn test_get_book_not_found() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::get()
        .uri("/books/nonexistent-id")
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);
}

#[actix_web::test]
async fn test_update_book() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Old Title", "author": "Old Author", "year": 2000, "isbn": "old-isbn"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    let body: serde_json::Value = test::read_body_json(&resp).await;
    let id = body["id"].as_str().unwrap().to_string();
    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", id))
        .set_json(&json!({"title": "New Title", "year": 2024}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::OK);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert_eq!(body["title"], "New Title");
    assert_eq!(body["year"], 2024);
    assert_eq!(body["author"], "Old Author");
    assert_eq!(body["isbn"], "old-isbn");
}

#[actix_web::test]
async fn test_update_book_not_found() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::put()
        .uri("/books/nonexistent")
        .set_json(&json!({"title": "New Title"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);
}

#[actix_web::test]
async fn test_update_book_empty_body() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::put()
        .uri("/books/some-id")
        .set_json(&json!({}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::BAD_REQUEST);
}

#[actix_web::test]
async fn test_delete_book() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "To Delete", "author": "Author", "year": 2020, "isbn": "isbn-del"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    let body: serde_json::Value = test::read_body_json(&resp).await;
    let id = body["id"].as_str().unwrap().to_string();
    let req = test::TestRequest::delete()
        .uri(&format!("/books/{}", id))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::NO_CONTENT);
    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", id))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);
}

#[actix_web::test]
async fn test_delete_book_not_found() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::delete()
        .uri("/books/nonexistent")
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::NOT_FOUND);
}

#[actix_web::test]
async fn test_create_book_optional_fields() {
    let db = make_test_db();
    let app = test::init_service(make_app(db)).await;
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&json!({"title": "Minimal Book", "author": "Author"}))
        .to_request();
    let resp = app.call(req).await.unwrap();
    assert_eq!(resp.status(), actix_web::http::StatusCode::CREATED);
    let body: serde_json::Value = test::read_body_json(&resp).await;
    assert_eq!(body["title"], "Minimal Book");
    assert!(body["year"].is_null());
    assert!(body["isbn"].is_null());
}