use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_collection::{build_app, db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

fn test_app() -> Router {
    let pool = db::init_pool(":memory:");
    build_app(pool)
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let request = match body {
        Some(b) => {
            builder = builder.header("content-type", "application/json");
            builder.body(Body::from(b.to_string())).unwrap()
        }
        None => builder.body(Body::empty()).unwrap(),
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
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();

    let (status, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"})),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["title"], "Dune");
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = test_app();

    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"author": "Nobody"})),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));

    let (status, _) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "   ", "author": "   "})),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = test_app();

    send(&app, "POST", "/books", Some(json!({"title": "A", "author": "Alice"}))).await;
    send(&app, "POST", "/books", Some(json!({"title": "B", "author": "Bob"}))).await;
    send(&app, "POST", "/books", Some(json!({"title": "C", "author": "Alice"}))).await;

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, alice) = send(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(alice.as_array().unwrap().len(), 2);
    for book in alice.as_array().unwrap() {
        assert_eq!(book["author"], "Alice");
    }
}

#[tokio::test]
async fn update_book() {
    let app = test_app();

    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Old", "author": "Author"})),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "New", "author": "Author", "year": 2020})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["year"], 2020);

    // Updating a non-existent book returns 404.
    let (status, _) = send(
        &app,
        "PUT",
        "/books/9999",
        Some(json!({"title": "X", "author": "Y"})),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book() {
    let app = test_app();

    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Temp", "author": "Author"})),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Deleting again returns 404.
    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/books/12345", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}
