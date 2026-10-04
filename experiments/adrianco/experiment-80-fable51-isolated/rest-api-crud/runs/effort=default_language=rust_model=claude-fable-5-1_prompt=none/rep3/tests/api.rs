use axum::{
    body::Body,
    http::{header, Method, Request, StatusCode},
    Router,
};
use books_api::{app, db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(db::open_in_memory().expect("in-memory database"))
}

/// Sends one request and returns the status plus the parsed JSON body
/// (`Value::Null` when the body is empty).
async fn send(app: &Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(json) => {
            builder = builder.header(header::CONTENT_TYPE, "application/json");
            Body::from(json.to_string())
        }
        None => Body::empty(),
    };
    let response = app
        .clone()
        .oneshot(builder.body(body).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("response body is JSON")
    };
    (status, value)
}

fn dune() -> Value {
    json!({ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" })
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

    let (status, created) = send(&app, Method::POST, "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    assert_eq!(created["isbn"], "9780441172719");
    let id = created["id"].as_i64().expect("numeric id");

    let (status, fetched) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_accepts_missing_optional_fields() {
    let app = test_app();
    let (status, body) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Emma", "author": "Jane Austen" })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(body["year"], Value::Null);
    assert_eq!(body["isbn"], Value::Null);
}

#[tokio::test]
async fn create_rejects_missing_or_blank_required_fields() {
    let app = test_app();

    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "year": 1965 }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(
        body["details"],
        json!(["title is required", "author is required"])
    );

    let (status, body) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "   ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["details"], json!(["title is required"]));

    // Nothing should have been stored.
    let (_, books) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(books, json!([]));
}

#[tokio::test]
async fn create_rejects_malformed_json() {
    let app = test_app();
    let request = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let response = app.oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let body: Value = serde_json::from_slice(&bytes).unwrap();
    assert!(body["error"].is_string());
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = test_app();
    send(&app, Method::POST, "/books", Some(dune())).await;
    send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969 })),
    )
    .await;
    send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Emma", "author": "Jane Austen", "year": 1815 })),
    )
    .await;

    let (status, all) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) = send(&app, Method::GET, "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let titles: Vec<_> = filtered
        .as_array()
        .unwrap()
        .iter()
        .map(|b| b["title"].as_str().unwrap())
        .collect();
    assert_eq!(titles, ["Dune", "Dune Messiah"]);

    let (_, none) = send(&app, Method::GET, "/books?author=Nobody", None).await;
    assert_eq!(none, json!([]));
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    let (_, created) = send(&app, Method::POST, "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, updated) = send(
        &app,
        Method::PUT,
        &uri,
        Some(json!({ "title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["id"], created["id"]);
    assert_eq!(updated["title"], "Dune (Revised)");
    assert_eq!(updated["year"], 1966);
    assert_eq!(updated["isbn"], Value::Null);

    let (_, fetched) = send(&app, Method::GET, &uri, None).await;
    assert_eq!(fetched, updated);

    let (status, _) = send(&app, Method::PUT, &uri, Some(json!({ "title": "No author" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn delete_book_removes_it() {
    let app = test_app();
    let (_, created) = send(&app, Method::POST, "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, body) = send(&app, Method::DELETE, &uri, None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, _) = send(&app, Method::GET, &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = send(&app, Method::DELETE, &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn unknown_and_invalid_ids_return_json_errors() {
    let app = test_app();

    let (status, body) = send(&app, Method::GET, "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book 999 not found");

    let (status, _) = send(&app, Method::PUT, "/books/999", Some(dune())).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, body) = send(&app, Method::GET, "/books/abc", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].is_string());
}
