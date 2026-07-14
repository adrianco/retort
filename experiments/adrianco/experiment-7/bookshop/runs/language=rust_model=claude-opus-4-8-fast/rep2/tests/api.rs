use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_collection::{build_app, Book};
use http_body_util::BodyExt;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

fn test_app() -> Router {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    build_app(conn).expect("build app")
}

async fn request(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let builder = Request::builder().method(method).uri(uri);
    let req = match body {
        Some(b) => builder
            .header("content-type", "application/json")
            .body(Body::from(b.to_string()))
            .unwrap(),
        None => builder.body(Body::empty()).unwrap(),
    };
    let resp = app.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, value)
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = request(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let (status, body) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123" })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let created: Book = serde_json::from_value(body).unwrap();
    assert_eq!(created.title, "Dune");
    assert_eq!(created.author, "Herbert");

    let (status, body) = request(&app, "GET", &format!("/books/{}", created.id), None).await;
    assert_eq!(status, StatusCode::OK);
    let fetched: Book = serde_json::from_value(body).unwrap();
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = test_app();
    let (status, body) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "author": "Nobody" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "  ", "author": "X" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = test_app();
    for (title, author) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        request(
            &app,
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
    }

    let (status, body) = request(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    let (status, body) = request(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();
    let (_, body) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Old", "author": "Auth" })),
    )
    .await;
    let id = body["id"].as_i64().unwrap();

    let (status, body) = request(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({ "title": "New", "author": "Auth", "year": 2020 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "New");
    assert_eq!(body["year"], 2020);

    let (status, _) = request(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = request(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn missing_book_returns_404() {
    let app = test_app();
    let (status, body) = request(&app, "GET", "/books/9999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}
