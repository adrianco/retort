use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_api::{app, init_db, Book};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(init_db(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let req = match body {
        Some(b) => Request::builder()
            .method(method)
            .uri(uri)
            .header("content-type", "application/json")
            .body(Body::from(b.to_string()))
            .unwrap(),
        None => Request::builder().method(method).uri(uri).body(Body::empty()).unwrap(),
    };
    let resp = app.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() { Value::Null } else { serde_json::from_slice(&bytes).unwrap() };
    (status, json)
}

#[tokio::test]
async fn health_check() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"})),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let created: Book = serde_json::from_value(body).unwrap();
    assert_eq!(created.title, "Dune");
    assert_eq!(created.year, Some(1965));

    let (status, body) = send(&app, "GET", &format!("/books/{}", created.id), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(serde_json::from_value::<Book>(body).unwrap(), created);
}

#[tokio::test]
async fn validation_rejects_missing_fields() {
    let app = test_app();
    let (status, body) = send(&app, "POST", "/books", Some(json!({"author": "X"}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) = send(&app, "POST", "/books", Some(json!({"title": "T", "author": "  "}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author is required");
}

#[tokio::test]
async fn list_with_author_filter() {
    let app = test_app();
    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        let (s, _) = send(&app, "POST", "/books", Some(json!({"title": t, "author": a}))).await;
        assert_eq!(s, StatusCode::CREATED);
    }
    let (status, body) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    let (status, body) = send(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    let books: Vec<Book> = serde_json::from_value(body).unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();
    let (_, body) = send(&app, "POST", "/books", Some(json!({"title": "Old", "author": "Me"}))).await;
    let id = body["id"].as_i64().unwrap();

    let (status, body) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "New", "author": "Me", "year": 2020})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "New");
    assert_eq!(body["year"], 2020);

    let (status, _) = send(&app, "PUT", &format!("/books/{id}"), Some(json!({"author": "Me"}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    let (status, _) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = send(&app, "PUT", "/books/9999", Some(json!({"title": "T", "author": "A"}))).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}
