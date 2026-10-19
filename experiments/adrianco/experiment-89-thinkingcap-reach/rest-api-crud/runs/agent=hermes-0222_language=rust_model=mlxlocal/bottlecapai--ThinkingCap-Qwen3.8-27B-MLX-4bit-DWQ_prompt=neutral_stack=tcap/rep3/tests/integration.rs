//! Integration tests: exercise the full HTTP stack (routing, JSON, status codes)
//! against an in-memory SQLite database.

use std::sync::{Arc, Mutex};

use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::Router;
use book_api::{init_db, router, AppState};
use serde_json::json;
use tower::ServiceExt;

fn app() -> Router {
    let conn = init_db(":memory:").unwrap();
    let state = AppState {
        db: Arc::new(Mutex::new(conn)),
    };
    router(state)
}

async fn get(app: &Router, uri: &str) -> axum::http::Response<Body> {
    let request = Request::builder().uri(uri).body(Body::empty()).unwrap();
    app.clone().oneshot(request).await.unwrap()
}

async fn post(app: &Router, uri: &str, body: &str) -> axum::http::Response<Body> {
    let request = Request::builder()
        .method("POST")
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap();
    app.clone().oneshot(request).await.unwrap()
}

async fn put(app: &Router, uri: &str, body: &str) -> axum::http::Response<Body> {
    let request = Request::builder()
        .method("PUT")
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap();
    app.clone().oneshot(request).await.unwrap()
}

async fn delete(app: &Router, uri: &str) -> axum::http::Response<Body> {
    let request = Request::builder()
        .method("DELETE")
        .uri(uri)
        .body(Body::empty())
        .unwrap();
    app.clone().oneshot(request).await.unwrap()
}

async fn body_json(response: axum::http::Response<Body>) -> serde_json::Value {
    let bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

/// Creates a book and returns its id.
async fn create(app: &Router, title: &str, author: &str) -> i64 {
    let response = post(
        app,
        "/books",
        &json!({ "title": title, "author": author }).to_string(),
    )
    .await;
    assert_eq!(response.status(), StatusCode::CREATED);
    body_json(response).await["id"].as_i64().unwrap()
}

// --- health & root ---

#[tokio::test]
async fn health_returns_ok() {
    let app = app();
    let response = get(&app, "/health").await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn root_returns_service_descriptor() {
    let app = app();
    let response = get(&app, "/").await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["service"], "book-api");
    assert_eq!(body["status"], "ok");
}

// --- POST /books ---

#[tokio::test]
async fn create_book_returns_201_with_all_fields() {
    let app = app();
    let response = post(
        &app,
        "/books",
        r#"{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}"#,
    )
    .await;
    assert_eq!(response.status(), StatusCode::CREATED);
    let body = body_json(response).await;
    assert_eq!(body["id"], 1);
    assert_eq!(body["title"], "Dune");
    assert_eq!(body["author"], "Frank Herbert");
    assert_eq!(body["year"], 1965);
    assert_eq!(body["isbn"], "978-0441172719");
}

#[tokio::test]
async fn create_book_without_optional_fields_succeeds() {
    let app = app();
    let response = post(&app, "/books", r#"{"title": "Beloved", "author": "Toni Morrison"}"#).await;
    assert_eq!(response.status(), StatusCode::CREATED);
    let body = body_json(response).await;
    assert!(body.get("year").is_none());
    assert!(body.get("isbn").is_none());
}

#[tokio::test]
async fn create_book_missing_title_returns_400() {
    let app = app();
    let response = post(&app, "/books", r#"{"author": "Toni Morrison"}"#).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let body = body_json(response).await;
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn create_book_missing_author_returns_400() {
    let app = app();
    let response = post(&app, "/books", r#"{"title": "Beloved"}"#).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let body = body_json(response).await;
    assert!(body["error"].as_str().unwrap().contains("author"));
}

#[tokio::test]
async fn create_book_blank_title_returns_400() {
    let app = app();
    let response = post(&app, "/books", r#"{"title": "   ", "author": "Someone"}"#).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn create_book_invalid_json_returns_400() {
    let app = app();
    let response = post(&app, "/books", "not valid json").await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

// --- GET /books ---

#[tokio::test]
async fn list_books_returns_all_books() {
    let app = app();
    create(&app, "Dune", "Frank Herbert").await;
    create(&app, "Foundation", "Isaac Asimov").await;

    let response = get(&app, "/books").await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body.as_array().unwrap().len(), 2);
    assert_eq!(body[0]["title"], "Dune");
    assert_eq!(body[1]["title"], "Foundation");
}

#[tokio::test]
async fn list_books_filters_by_author() {
    let app = app();
    create(&app, "Dune", "Frank Herbert").await;
    create(&app, "Foundation", "Isaac Asimov").await;
    create(&app, "Foundation and Empire", "Isaac Asimov").await;

    let response = get(&app, "/books?author=Isaac%20Asimov").await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Isaac Asimov"));
}

#[tokio::test]
async fn list_books_author_filter_no_match_returns_empty() {
    let app = app();
    create(&app, "Dune", "Frank Herbert").await;

    let response = get(&app, "/books?author=Nobody").await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body.as_array().unwrap().len(), 0);
}

// --- GET /books/{id} ---

#[tokio::test]
async fn get_book_by_id_returns_book() {
    let app = app();
    let id = create(&app, "Dune", "Frank Herbert").await;

    let response = get(&app, &format!("/books/{id}")).await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["id"], id);
    assert_eq!(body["title"], "Dune");
}

#[tokio::test]
async fn get_book_not_found_returns_404() {
    let app = app();
    let response = get(&app, "/books/999").await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let body = body_json(response).await;
    assert!(body["error"].as_str().unwrap().contains("not found"));
}

// --- PUT /books/{id} ---

#[tokio::test]
async fn update_book_overwrites_provided_fields_only() {
    let app = app();
    let id = create(&app, "Dune", "Frank Herbert").await;

    let response = put(&app, &format!("/books/{id}"), r#"{"year": 1966}"#).await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["year"], 1966);
    // Untouched fields are preserved.
    assert_eq!(body["title"], "Dune");
    assert_eq!(body["author"], "Frank Herbert");
}

#[tokio::test]
async fn update_book_changes_title_and_author() {
    let app = app();
    let id = create(&app, "Old Title", "Old Author").await;

    let response = put(
        &app,
        &format!("/books/{id}"),
        r#"{"title": "New Title", "author": "New Author"}"#,
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["title"], "New Title");
    assert_eq!(body["author"], "New Author");

    // Persisted, not just echoed back.
    let response = get(&app, &format!("/books/{id}")).await;
    let body = body_json(response).await;
    assert_eq!(body["title"], "New Title");
}

#[tokio::test]
async fn update_book_not_found_returns_404() {
    let app = app();
    let response = put(&app, "/books/999", r#"{"title": "Ghost"}"#).await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_book_empty_author_returns_400() {
    let app = app();
    let id = create(&app, "Dune", "Frank Herbert").await;
    let response = put(&app, &format!("/books/{id}"), r#"{"author": ""}"#).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

// --- DELETE /books/{id} ---

#[tokio::test]
async fn delete_book_returns_204_and_removes_it() {
    let app = app();
    let id = create(&app, "Dune", "Frank Herbert").await;

    let response = delete(&app, &format!("/books/{id}")).await;
    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    let response = get(&app, &format!("/books/{id}")).await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book_not_found_returns_404() {
    let app = app();
    let response = delete(&app, "/books/999").await;
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
