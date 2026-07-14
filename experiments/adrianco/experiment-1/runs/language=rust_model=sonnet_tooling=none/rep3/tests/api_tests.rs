use actix_web::{test, web, App};
use book_api::{db, handlers, DbPool};
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use serde_json::{json, Value};

fn create_test_pool() -> DbPool {
    let manager = SqliteConnectionManager::memory();
    let pool = Pool::new(manager).expect("Failed to create test pool");
    db::init_db(&pool).expect("Failed to init test DB");
    pool
}

macro_rules! make_app {
    ($pool:expr) => {
        test::init_service(
            App::new()
                .app_data(web::Data::new($pool))
                .route("/health", web::get().to(handlers::health_check))
                .route("/books", web::post().to(handlers::create_book))
                .route("/books", web::get().to(handlers::list_books))
                .route("/books/{id}", web::get().to(handlers::get_book))
                .route("/books/{id}", web::put().to(handlers::update_book))
                .route("/books/{id}", web::delete().to(handlers::delete_book)),
        )
        .await
    };
}

#[actix_web::test]
async fn test_health_check() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: Value = test::read_body_json(resp).await;
    assert_eq!(body["status"], "ok");
}

#[actix_web::test]
async fn test_create_book_success() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2019,
            "isbn": "978-1718500440"
        }))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    let body: Value = test::read_body_json(resp).await;
    assert_eq!(body["title"], "The Rust Programming Language");
    assert_eq!(body["author"], "Steve Klabnik");
    assert!(body["id"].is_string());
}

#[actix_web::test]
async fn test_create_book_missing_title() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({"author": "Steve Klabnik"}))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let body: Value = test::read_body_json(resp).await;
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[actix_web::test]
async fn test_create_book_missing_author() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({"title": "Some Book"}))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    let body: Value = test::read_body_json(resp).await;
    assert!(body["error"].as_str().unwrap().contains("author"));
}

#[actix_web::test]
async fn test_list_books() {
    let app = make_app!(create_test_pool());

    for (title, author) in [("Book A", "Author One"), ("Book B", "Author Two")] {
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(json!({"title": title, "author": author}))
            .to_request();
        test::call_service(&app, req).await;
    }

    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: Value = test::read_body_json(resp).await;
    assert_eq!(body.as_array().unwrap().len(), 2);
}

#[actix_web::test]
async fn test_list_books_with_author_filter() {
    let app = make_app!(create_test_pool());

    for (title, author) in [("Book A", "Alice"), ("Book B", "Bob"), ("Book C", "Alice")] {
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(json!({"title": title, "author": author}))
            .to_request();
        test::call_service(&app, req).await;
    }

    let req = test::TestRequest::get()
        .uri("/books?author=Alice")
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: Value = test::read_body_json(resp).await;
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Alice"));
}

#[actix_web::test]
async fn test_get_book_by_id() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965}))
        .to_request();
    let resp = test::call_service(&app, req).await;
    let created: Value = test::read_body_json(resp).await;
    let id = created["id"].as_str().unwrap().to_string();

    let req = test::TestRequest::get()
        .uri(&format!("/books/{}", id))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: Value = test::read_body_json(resp).await;
    assert_eq!(body["title"], "Dune");
    assert_eq!(body["author"], "Frank Herbert");
}

#[actix_web::test]
async fn test_get_book_not_found() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::get()
        .uri("/books/nonexistent-id")
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}

#[actix_web::test]
async fn test_update_book() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({"title": "Original Title", "author": "Original Author"}))
        .to_request();
    let resp = test::call_service(&app, req).await;
    let created: Value = test::read_body_json(resp).await;
    let id = created["id"].as_str().unwrap().to_string();

    let req = test::TestRequest::put()
        .uri(&format!("/books/{}", id))
        .set_json(json!({"title": "Updated Title", "year": 2024}))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: Value = test::read_body_json(resp).await;
    assert_eq!(body["title"], "Updated Title");
    assert_eq!(body["author"], "Original Author");
    assert_eq!(body["year"], 2024);
}

#[actix_web::test]
async fn test_delete_book() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(json!({"title": "To Delete", "author": "Some Author"}))
        .to_request();
    let resp = test::call_service(&app, req).await;
    let created: Value = test::read_body_json(resp).await;
    let id = created["id"].as_str().unwrap().to_string();

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

#[actix_web::test]
async fn test_delete_book_not_found() {
    let app = make_app!(create_test_pool());

    let req = test::TestRequest::delete()
        .uri("/books/nonexistent-id")
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}
