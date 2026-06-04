//! Integration tests exercising the router directly via `tower`'s oneshot.

use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_collection::{app, init_db, Book};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

/// Build a fresh app backed by an in-memory database.
fn test_app() -> Router {
    let conn = init_db(":memory:").expect("init db");
    app(conn)
}

/// Send a request and return (status, parsed JSON body or Null for empty).
async fn send(router: Router, req: Request<Body>) -> (StatusCode, Value) {
    let res = router.oneshot(req).await.unwrap();
    let status = res.status();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let body = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, body)
}

fn post_book(body: Value) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let (status, body) = send(
        test_app(),
        Request::builder().uri("/health").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_and_get_book() {
    let router = test_app();

    let (status, created) = send(
        router.clone(),
        post_book(json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "9781593278281"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "The Rust Programming Language");
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(
        router,
        Request::builder()
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let book: Book = serde_json::from_value(fetched).unwrap();
    assert_eq!(book.author, "Steve Klabnik");
    assert_eq!(book.year, Some(2018));
}

#[tokio::test]
async fn create_requires_title_and_author() {
    // Missing author.
    let (status, body) = send(
        test_app(),
        post_book(json!({ "title": "No Author" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("author"));

    // Blank title (whitespace only).
    let (status, body) = send(
        test_app(),
        post_book(json!({ "title": "   ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_with_author_filter() {
    let router = test_app();
    for book in [
        json!({ "title": "A", "author": "Alice" }),
        json!({ "title": "B", "author": "Bob" }),
        json!({ "title": "C", "author": "Alice" }),
    ] {
        let (status, _) = send(router.clone(), post_book(book)).await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = send(
        router.clone(),
        Request::builder().uri("/books").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, alice) = send(
        router,
        Request::builder()
            .uri("/books?author=Alice")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(alice.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn update_and_delete_book() {
    let router = test_app();

    let (_, created) = send(
        router.clone(),
        post_book(json!({ "title": "Old Title", "author": "Author" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    // Update.
    let (status, updated) = send(
        router.clone(),
        Request::builder()
            .method("PUT")
            .uri(format!("/books/{id}"))
            .header("content-type", "application/json")
            .body(Body::from(
                json!({ "title": "New Title", "author": "Author", "year": 2020 }).to_string(),
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New Title");
    assert_eq!(updated["year"], 2020);

    // Delete.
    let (status, _) = send(
        router.clone(),
        Request::builder()
            .method("DELETE")
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    // Now gone.
    let (status, _) = send(
        router,
        Request::builder()
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let (status, body) = send(
        test_app(),
        Request::builder()
            .uri("/books/9999")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body["error"].as_str().unwrap().contains("not found"));
}
