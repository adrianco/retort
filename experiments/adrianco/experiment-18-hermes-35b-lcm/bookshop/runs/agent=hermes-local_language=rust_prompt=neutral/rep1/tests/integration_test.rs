use book_api::{create_pool, create_router, Book};
use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use sqlx::SqlitePool;
use tower::ServiceExt;

fn new_pool() -> SqlitePool {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap()
        .block_on(async {
            let pool = create_pool("test_db.db").await;
            // Clean up old data
            sqlx::query("DELETE FROM books").execute(&pool).await.unwrap();
            pool
        })
}

fn get_router(pool: SqlitePool) -> Router {
    create_router(pool)
}

#[tokio::test]
async fn test_health_check() {
    let pool = new_pool();
    let app = get_router(pool);

    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let body_str = String::from_utf8(body.to_vec()).unwrap();
    assert!(body_str.contains("ok"));
}

#[tokio::test]
async fn test_create_book() {
    let pool = new_pool();
    let app = get_router(pool);

    let body = serde_json::json!({
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik",
        "year": 2018,
        "isbn": "978-1-7185-0044-8"
    });

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Book = serde_json::from_slice(&body_bytes).unwrap();

    assert_eq!(book.title, "The Rust Programming Language");
    assert_eq!(book.author, "Steve Klabnik");
    assert_eq!(book.year, Some(2018));
    assert_eq!(book.isbn, Some("978-1-7185-0044-8".to_string()));
    assert!(!book.id.is_empty());
}

#[tokio::test]
async fn test_create_book_missing_title() {
    let pool = new_pool();
    let app = get_router(pool);

    let body = serde_json::json!({
        "author": "Someone",
        "year": 2020
    });

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_create_book_missing_author() {
    let pool = new_pool();
    let app = get_router(pool);

    let body = serde_json::json!({
        "title": "Some Book"
    });

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_list_books() {
    let pool = new_pool();
    let app = get_router(pool);

    // Create first book
    let body1 = serde_json::json!({
        "title": "Book A",
        "author": "Author One",
        "year": 2020,
        "isbn": "111"
    });
    app.clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body1).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    // Create second book by different author
    let body2 = serde_json::json!({
        "title": "Book B",
        "author": "Author Two",
        "year": 2021,
        "isbn": "222"
    });
    app.clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body2).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    // List all
    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let books: Vec<Book> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 2);
}

#[tokio::test]
async fn test_list_books_filter_by_author() {
    let pool = new_pool();
    let app = get_router(pool);

    // Create books by same author
    let body1 = serde_json::json!({
        "title": "Book A",
        "author": "Steve Klabnik",
        "year": 2018
    });
    app.clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body1).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    let body2 = serde_json::json!({
        "title": "Book B",
        "author": "Carol Nichols",
        "year": 2019
    });
    app.clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body2).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    // Filter by "Steve"
    let response = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Steve")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let books: Vec<Book> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0].author, "Steve Klabnik");
}

#[tokio::test]
async fn test_get_book() {
    let pool = new_pool();
    let app = get_router(pool);

    // Create a book first
    let body = serde_json::json!({
        "title": "Get Me",
        "author": "Get Author",
        "year": 2022
    });
    let create_resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    let body_bytes = axum::body::to_bytes(create_resp.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Book = serde_json::from_slice(&body_bytes).unwrap();

    // Get by ID
    let response = app
        .oneshot(
            Request::builder()
                .uri(&format!("/books/{}", book.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let fetched: Book = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(fetched.id, book.id);
    assert_eq!(fetched.title, "Get Me");
}

#[tokio::test]
async fn test_get_book_not_found() {
    let pool = new_pool();
    let app = get_router(pool);

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books/nonexistent-id")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_book() {
    let pool = new_pool();
    let app = get_router(pool);

    // Create a book
    let body = serde_json::json!({
        "title": "Old Title",
        "author": "Old Author",
        "year": 2020
    });
    let create_resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    let body_bytes = axum::body::to_bytes(create_resp.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Book = serde_json::from_slice(&body_bytes).unwrap();

    // Update the book
    let update_body = serde_json::json!({
        "title": "New Title"
    });
    let response = app
        .oneshot(
            Request::builder()
                .uri(&format!("/books/{}", book.id))
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&update_body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let updated: Book = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(updated.title, "New Title");
    assert_eq!(updated.author, "Old Author"); // unchanged
    assert_eq!(updated.id, book.id);
}

#[tokio::test]
async fn test_delete_book() {
    let pool = new_pool();
    let app = get_router(pool);

    // Create a book
    let body = serde_json::json!({
        "title": "To Delete",
        "author": "Delete Author",
        "year": 2023
    });
    let create_resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    let body_bytes = axum::body::to_bytes(create_resp.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Book = serde_json::from_slice(&body_bytes).unwrap();

    // Delete it
    let response = app
        .oneshot(
            Request::builder()
                .uri(&format!("/books/{}", book.id))
                .method("DELETE")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    // Verify it's gone
    let get_response = app
        .oneshot(
            Request::builder()
                .uri(&format!("/books/{}", book.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(get_response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_delete_book_not_found() {
    let pool = new_pool();
    let app = get_router(pool);

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books/nonexistent")
                .method("DELETE")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_create_book_minimal_fields() {
    let pool = new_pool();
    let app = get_router(pool);

    // Only title and author are required; year and isbn are optional
    let body = serde_json::json!({
        "title": "Minimal Book",
        "author": "Some Author"
    });

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Book = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book.title, "Minimal Book");
    assert_eq!(book.year, None);
    assert_eq!(book.isbn, None);
}

#[tokio::test]
async fn test_update_nonexistent_book() {
    let pool = new_pool();
    let app = get_router(pool);

    let update_body = serde_json::json!({
        "title": "Nobody"
    });

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books/fake-id")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_string(&update_body).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
