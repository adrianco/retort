use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
    Router,
};
use book_collection::{app, AppState};
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt;

fn setup() -> Router {
    app(AppState::new(Connection::open_in_memory().unwrap()).unwrap())
}
async fn request(
    app: &Router,
    method: &str,
    uri: &str,
    body: Option<Value>,
) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(value) => {
            builder = builder.header("content-type", "application/json");
            Body::from(value.to_string())
        }
        None => Body::empty(),
    };
    let response = app
        .clone()
        .oneshot(builder.body(body).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    (status, serde_json::from_slice(&bytes).unwrap())
}
fn book(title: &str, author: &str) -> Value {
    json!({"title": title, "author": author, "year": 2020, "isbn": "123"})
}

#[tokio::test]
async fn create_get_update_delete() {
    let app = setup();
    let (status, created) = request(&app, "POST", "/books", Some(book("One", "Alice"))).await;
    assert_eq!(status, StatusCode::CREATED);
    let id = created["id"].as_i64().unwrap();
    let path = format!("/books/{id}");
    assert_eq!(request(&app, "GET", &path, None).await.1, created);
    let (status, updated) = request(&app, "PUT", &path, Some(book("Two", "Bob"))).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Two");
    assert_eq!(updated["author"], "Bob");
    assert_eq!(request(&app, "DELETE", &path, None).await.0, StatusCode::OK);
    assert_eq!(
        request(&app, "GET", &path, None).await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(
        request(&app, "DELETE", &path, None).await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(
        request(&app, "PUT", &path, Some(book("Two", "Bob")))
            .await
            .0,
        StatusCode::NOT_FOUND
    );
}

#[tokio::test]
async fn list_and_filter() {
    let app = setup();
    request(&app, "POST", "/books", Some(book("One", "Alice"))).await;
    request(&app, "POST", "/books", Some(book("Two", "Bob"))).await;
    assert_eq!(
        request(&app, "GET", "/books", None)
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        2
    );
    let filtered = request(&app, "GET", "/books?author=Alice", None).await.1;
    assert_eq!(filtered.as_array().unwrap().len(), 1);
    assert_eq!(filtered[0]["author"], "Alice");
    assert!(request(&app, "GET", "/books?author=Nobody", None)
        .await
        .1
        .as_array()
        .unwrap()
        .is_empty());
}

#[tokio::test]
async fn validates_create_and_update() {
    let app = setup();
    for input in [
        book(" ", "Alice"),
        book("Title", ""),
        json!({"author":"Alice", "year":2020, "isbn":"123"}),
    ] {
        let (status, body) = request(&app, "POST", "/books", Some(input.clone())).await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert!(body["error"].is_string());
        assert_eq!(
            request(&app, "PUT", "/books/1", Some(input)).await.0,
            StatusCode::BAD_REQUEST
        );
    }
    assert!(request(&app, "GET", "/books", None)
        .await
        .1
        .as_array()
        .unwrap()
        .is_empty());
}

#[tokio::test]
async fn health_check() {
    let (status, body) = request(&setup(), "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}
