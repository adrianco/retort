use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use serde_json::json;
use tower::ServiceExt;

use book_api::db::init_pool;
use book_api::routes::create_router;

fn get_test_db_path() -> String {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let path = manifest.join("test_books.db");
    // Delete old file, then explicitly create it
    let _ = std::fs::remove_file(&path);
    // Pre-create the file
    if let Ok(f) = std::fs::File::create(&path) {
        drop(f);
    }
    path.to_str().unwrap().to_string()
}

fn cleanup_db(path: &str) {
    let _ = std::fs::remove_file(path);
}

fn setup_test() -> (sqlx::SqlitePool, Router) {
    use sqlx::SqlitePool;
    use axum::Router;
    
    let db_path = get_test_db_path();
    
    eprintln!("DEBUG: db_path = {}", db_path);
    eprintln!("DEBUG: file exists before connect: {}", std::path::Path::new(&db_path).exists());
    eprintln!("DEBUG: file size: {}", std::fs::metadata(&db_path).unwrap().len());
    
    let pool = init_pool(&db_path).expect("Failed to create pool");
    eprintln!("DEBUG: Pool created successfully");
    
    let app = create_router(pool.clone());
    (pool, app)
}

#[tokio::test]
async fn test_health_check() {
    let (pool, app) = setup_test();
    let _ = pool;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .method("GET")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["data"]["status"], "ok");

    cleanup_db("test_books.db");
}

#[tokio::test]
async fn test_create_and_get_book() {
    let (pool, app) = setup_test();
    let _ = pool;

    let create_body = json!({
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .method("POST")
                .header("Content-Type", "application/json")
                .body(Body::from(create_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let book_id = json["data"]["id"].as_str().unwrap();

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", book_id))
                .method("GET")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let data = &json["data"];
    assert_eq!(data["title"], "The Great Gatsby");
    assert_eq!(data["author"], "F. Scott Fitzgerald");
    assert_eq!(data["year"], 1925);

    cleanup_db("test_books.db");
}

#[tokio::test]
async fn test_list_books_with_author_filter() {
    let (pool, app) = setup_test();
    let _ = pool;

    let book1 = json!({
        "title": "Book One",
        "author": "Test Author",
        "year": 2020,
        "isbn": "0000000001"
    });

    let book2 = json!({
        "title": "Book Two",
        "author": "Test Author",
        "year": 2021,
        "isbn": "0000000002"
    });

    let book3 = json!({
        "title": "Other Book",
        "author": "Other Author",
        "year": 2022,
        "isbn": "0000000003"
    });

    for (target_uri, target_body) in [
        ("/books", book1),
        ("/books", book2),
        ("/books", book3),
    ] {
        let _ = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri(target_uri)
                    .method("POST")
                    .header("Content-Type", "application/json")
                    .body(Body::from(target_body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
    }

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .method("GET")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let all_books = json["data"].as_array().unwrap();
    assert_eq!(all_books.len(), 3);

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Test%20Author")
                .method("GET")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let filtered = json["data"].as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    for book in filtered {
        assert_eq!(book["author"], "Test Author");
    }

    cleanup_db("test_books.db");
}

#[tokio::test]
async fn test_update_book() {
    let (pool, app) = setup_test();
    let _ = pool;

    let create_body = json!({
        "title": "Original Title",
        "author": "Original Author",
        "year": 2000,
        "isbn": "1111111111"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .method("POST")
                .header("Content-Type", "application/json")
                .body(Body::from(create_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let book_id = json["data"]["id"].as_str().unwrap();

    let update_body = json!({
        "title": "Updated Title"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", book_id))
                .method("PUT")
                .header("Content-Type", "application/json")
                .body(Body::from(update_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let data = &json["data"];
    assert_eq!(data["title"], "Updated Title");
    assert_eq!(data["author"], "Original Author");

    cleanup_db("test_books.db");
}

#[tokio::test]
async fn test_delete_book() {
    let (pool, app) = setup_test();
    let _ = pool;

    let create_body = json!({
        "title": "To Delete",
        "author": "Author",
        "year": 2020,
        "isbn": "2222222222"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .method("POST")
                .header("Content-Type", "application/json")
                .body(Body::from(create_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let book_id = json["data"]["id"].as_str().unwrap();

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", book_id))
                .method("DELETE")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", book_id))
                .method("GET")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);

    cleanup_db("test_books.db");
}

#[tokio::test]
async fn test_validation_missing_fields() {
    let (pool, app) = setup_test();
    let _ = pool;

    let invalid_body = json!({
        "author": "Some Author",
        "year": 2020,
        "isbn": "1234567890"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .method("POST")
                .header("Content-Type", "application/json")
                .body(Body::from(invalid_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);

    let empty_title_body = json!({
        "title": "",
        "author": "Some Author"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .method("POST")
                .header("Content-Type", "application/json")
                .body(Body::from(empty_title_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    cleanup_db("test_books.db");
}
