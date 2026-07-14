use axum::{
    body::{to_bytes, Body},
    http::{Method, Request, StatusCode},
    Router,
};
use books_api::{app, db, models::Book, Db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use std::sync::{Arc, Mutex};
use tower::ServiceExt;

fn test_app() -> Router {
    let conn = db::open_in_memory().expect("open in-memory db");
    let db: Db = Arc::new(Mutex::new(conn));
    app(db)
}

async fn json_body(body: Body) -> Value {
    let bytes = body.collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap_or(Value::Null)
}

async fn send(app: Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let req = match body {
        Some(b) => {
            builder = builder.header("content-type", "application/json");
            builder.body(Body::from(b.to_string())).unwrap()
        }
        None => builder.body(Body::empty()).unwrap(),
    };
    let resp = app.oneshot(req).await.unwrap();
    let status = resp.status();
    let value = json_body(resp.into_body()).await;
    (status, value)
}

#[tokio::test]
async fn health_endpoint_returns_ok() {
    let app = test_app();
    let (status, body) = send(app, Method::GET, "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_book_returns_created_and_assigns_id() {
    let app = test_app();
    let payload = json!({
        "title": "The Pragmatic Programmer",
        "author": "Andy Hunt",
        "year": 1999,
        "isbn": "9780201616224"
    });
    let (status, body) = send(app, Method::POST, "/books", Some(payload)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert!(body["id"].as_i64().unwrap() > 0);
    assert_eq!(body["title"], "The Pragmatic Programmer");
    assert_eq!(body["author"], "Andy Hunt");
    assert_eq!(body["year"], 1999);
}

#[tokio::test]
async fn create_book_validates_required_fields() {
    let app = test_app();
    let payload = json!({ "author": "Anonymous" });
    let (status, body) = send(app, Method::POST, "/books", Some(payload)).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = test_app();

    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        let (status, _) = send(
            app.clone(),
            Method::POST,
            "/books",
            Some(json!({ "title": t, "author": a })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, body) = send(app.clone(), Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    let (status, body) = send(app, Method::GET, "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    let books: Vec<Book> = serde_json::from_value(body).unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "Alice"));
}

#[tokio::test]
async fn get_update_delete_book_lifecycle() {
    let app = test_app();

    let (status, created) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(json!({ "title": "Old", "author": "Author" })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let id = created["id"].as_i64().unwrap();

    let (status, body) = send(app.clone(), Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "Old");

    let (status, body) = send(
        app.clone(),
        Method::PUT,
        &format!("/books/{id}"),
        Some(json!({ "title": "New", "author": "Author", "year": 2020 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "New");
    assert_eq!(body["year"], 2020);

    let (status, _) = send(app.clone(), Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let (status, body) = send(app, Method::GET, "/books/99999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body["error"].as_str().unwrap().contains("not found"));
}

// Silence unused-import lint for to_bytes when http-body-util provides collect API
#[allow(dead_code)]
async fn _unused(body: Body) {
    let _ = to_bytes(body, usize::MAX).await;
}
