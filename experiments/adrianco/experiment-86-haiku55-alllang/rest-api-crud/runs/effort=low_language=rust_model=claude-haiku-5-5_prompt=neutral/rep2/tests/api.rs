use axum::{
    body::Body,
    http::{Method, Request, StatusCode},
    Router,
};
use http_body_util::BodyExt;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    book_api::app(Connection::open_in_memory().unwrap()).unwrap()
}

/// Sends a request and returns the status plus the parsed JSON body (Null when empty).
async fn send(app: &Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let builder = Request::builder().method(method).uri(uri);
    let request = match body {
        Some(v) => builder
            .header("content-type", "application/json")
            .body(Body::from(v.to_string()))
            .unwrap(),
        None => builder.body(Body::empty()).unwrap(),
    };
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, value)
}

async fn create(app: &Router, title: &str, author: &str) -> Value {
    let (status, body) = send(
        app,
        Method::POST,
        "/books",
        Some(json!({ "title": title, "author": author, "year": 1965, "isbn": "9780441013593" })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    body
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = send(&app, Method::GET, "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_then_get_book() {
    let app = test_app();
    let created = create(&app, "Dune", "Frank Herbert").await;
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    assert_eq!(created["isbn"], "9780441013593");
    let id = created["id"].as_i64().unwrap();

    let (status, body) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, created);
}

#[tokio::test]
async fn create_rejects_missing_title_or_author() {
    let app = test_app();
    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "author": "A" }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["error"], "title is required");

    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "title": "T", "author": "  " }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["error"], "author is required");

    let (status, _) = send(&app, Method::POST, "/books", Some(json!({ "title": "T" }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn malformed_json_returns_bad_request_json_error() {
    let app = test_app();
    let request = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{oops"))
        .unwrap();
    let response = app.clone().oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let body: Value = serde_json::from_slice(&bytes).unwrap();
    assert!(body["error"].as_str().unwrap().starts_with("invalid JSON body"));
}

#[tokio::test]
async fn list_books_filters_by_author_case_insensitively() {
    let app = test_app();
    create(&app, "Dune", "Frank Herbert").await;
    create(&app, "Emperor of Dune", "frank herbert").await;
    create(&app, "Neuromancer", "William Gibson").await;

    let (status, all) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) = send(&app, Method::GET, "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let titles: Vec<&str> = filtered
        .as_array()
        .unwrap()
        .iter()
        .map(|b| b["title"].as_str().unwrap())
        .collect();
    assert_eq!(titles, vec!["Dune", "Emperor of Dune"]);
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    let created = create(&app, "Dune", "Frank Herbert").await;
    let id = created["id"].as_i64().unwrap();

    let (status, body) = send(
        &app,
        Method::PUT,
        &format!("/books/{id}"),
        Some(json!({ "title": "Dune (Revised)", "author": "Frank Herbert" })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "Dune (Revised)");
    assert_eq!(body["year"], Value::Null);
    assert_eq!(body["isbn"], Value::Null);

    let (_, fetched) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(fetched, body);
}

#[tokio::test]
async fn update_missing_book_returns_not_found() {
    let app = test_app();
    let (status, body) = send(
        &app,
        Method::PUT,
        "/books/999",
        Some(json!({ "title": "T", "author": "A" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}

#[tokio::test]
async fn delete_book_then_get_returns_not_found() {
    let app = test_app();
    let created = create(&app, "Dune", "Frank Herbert").await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = send(&app, Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_unknown_book_returns_not_found() {
    let app = test_app();
    let (status, body) = send(&app, Method::GET, "/books/42", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}
