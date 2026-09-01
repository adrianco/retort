//! Integration tests exercising the HTTP API end-to-end against an in-memory SQLite DB.

use axum::body::Body;
use axum::http::{header, Method, Request, StatusCode};
use axum::Router;
use book_api::{app, Db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(Db::in_memory().expect("in-memory db"))
}

async fn send(app: &Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            req = req.header(header::CONTENT_TYPE, "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let resp = app
        .clone()
        .oneshot(req.body(body).unwrap())
        .await
        .expect("request failed");
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("response should be JSON")
    };
    (status, json)
}

fn dune() -> Value {
    json!({ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" })
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = send(&app, Method::GET, "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
    assert_eq!(body["database"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();

    let (status, created) = send(&app, Method::POST, "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["id"], 1);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    assert_eq!(created["isbn"], "978-0441013593");

    let (status, fetched) = send(&app, Method::GET, "/books/1", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_rejects_missing_required_fields() {
    let app = test_app();

    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "year": 2001 }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["error"], "validation failed");
    let details = body["details"].as_array().unwrap();
    assert!(details.iter().any(|d| d == "title is required"));
    assert!(details.iter().any(|d| d == "author is required"));

    // Whitespace-only title is also rejected.
    let (status, _) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "  ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    // Nothing was persisted.
    let (_, list) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(list.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn create_rejects_malformed_json() {
    let app = test_app();
    let req = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from("{ not json"))
        .unwrap();
    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = test_app();
    send(&app, Method::POST, "/books", Some(dune())).await;
    send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin" })),
    )
    .await;
    send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Children of Dune", "author": "Frank Herbert" })),
    )
    .await;

    let (status, all) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, herbert) = send(&app, Method::GET, "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let herbert = herbert.as_array().unwrap();
    assert_eq!(herbert.len(), 2);
    assert!(herbert.iter().all(|b| b["author"] == "Frank Herbert"));

    let (_, none) = send(&app, Method::GET, "/books?author=Nobody", None).await;
    assert_eq!(none.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    send(&app, Method::POST, "/books", Some(dune())).await;

    let (status, updated) = send(
        &app,
        Method::PUT,
        "/books/1",
        Some(json!({ "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["id"], 1);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["year"], 1969);
    // isbn was omitted in the PUT body, so it is cleared.
    assert!(updated.get("isbn").is_none());

    let (_, fetched) = send(&app, Method::GET, "/books/1", None).await;
    assert_eq!(fetched, updated);

    // Validation applies to updates too.
    let (status, _) = send(&app, Method::PUT, "/books/1", Some(json!({ "title": "X" }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    // Updating a missing book is 404.
    let (status, body) = send(&app, Method::PUT, "/books/999", Some(dune())).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book 999 not found");
}

#[tokio::test]
async fn delete_book_then_404() {
    let app = test_app();
    send(&app, Method::POST, "/books", Some(dune())).await;

    let (status, body) = send(&app, Method::DELETE, "/books/1", None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, body) = send(&app, Method::GET, "/books/1", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book 1 not found");

    let (status, _) = send(&app, Method::DELETE, "/books/1", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn non_numeric_id_is_bad_request() {
    let app = test_app();
    let (status, body) = send(&app, Method::GET, "/books/abc", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("abc") || body["error"].is_string());
}
