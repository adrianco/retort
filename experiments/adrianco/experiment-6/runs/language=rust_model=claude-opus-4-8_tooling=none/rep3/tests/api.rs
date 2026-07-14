//! Integration tests exercising the router end-to-end over an in-memory DB.

use std::sync::{Arc, Mutex};

use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_api::{app, init_schema, Book};
use http_body_util::BodyExt;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

fn test_app() -> Router {
    let conn = Connection::open_in_memory().unwrap();
    init_schema(&conn).unwrap();
    app(Arc::new(Mutex::new(conn)))
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let request = Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json");
    let request = match body {
        Some(b) => request.body(Body::from(b.to_string())).unwrap(),
        None => request.body(Body::empty()).unwrap(),
    };

    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let value: Value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, value)
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_then_get_book() {
    let app = test_app();

    let (status, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "9781593278281"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let book: Book = serde_json::from_value(created).unwrap();
    assert_eq!(book.id, 1);
    assert_eq!(book.title, "The Rust Programming Language");

    let (status, fetched) = send(&app, "GET", "/books/1", None).await;
    assert_eq!(status, StatusCode::OK);
    let fetched: Book = serde_json::from_value(fetched).unwrap();
    assert_eq!(fetched, book);
}

#[tokio::test]
async fn create_requires_title_and_author() {
    let app = test_app();

    let (status, body) = send(&app, "POST", "/books", Some(json!({ "author": "Nobody" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Untitled", "author": "   " })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author is required");
}

#[tokio::test]
async fn list_with_author_filter() {
    let app = test_app();
    for (title, author) in [
        ("Book A", "Alice"),
        ("Book B", "Bob"),
        ("Book C", "Alice"),
    ] {
        send(
            &app,
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
    }

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, alice) = send(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    let alice = alice.as_array().unwrap();
    assert_eq!(alice.len(), 2);
    assert!(alice.iter().all(|b| b["author"] == "Alice"));
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Old", "author": "Author", "year": 2000 })),
    )
    .await;

    let (status, updated) = send(
        &app,
        "PUT",
        "/books/1",
        Some(json!({ "title": "New", "author": "Author", "year": 2024 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["year"], 2024);

    let (_, fetched) = send(&app, "GET", "/books/1", None).await;
    assert_eq!(fetched["title"], "New");
}

#[tokio::test]
async fn delete_book_then_404() {
    let app = test_app();
    send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Doomed", "author": "Author" })),
    )
    .await;

    let (status, _) = send(&app, "DELETE", "/books/1", None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(&app, "GET", "/books/1", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, "DELETE", "/books/1", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}
