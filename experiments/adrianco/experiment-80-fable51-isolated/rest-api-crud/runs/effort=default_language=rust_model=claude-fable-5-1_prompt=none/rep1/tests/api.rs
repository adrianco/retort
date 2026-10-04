use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    books_api::app(books_api::open_db(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let builder = Request::builder().method(method).uri(uri);
    let request = match body {
        Some(json) => builder
            .header("content-type", "application/json")
            .body(Body::from(json.to_string()))
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

fn dune() -> Value {
    json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"})
}

#[tokio::test]
async fn health_check() {
    let (status, body) = send(&test_app(), "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({"status": "ok"}));
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let (status, created) = send(&app, "POST", "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["year"], 1965);

    let id = created["id"].as_i64().unwrap();
    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_requires_title_and_author() {
    let app = test_app();
    let (status, body) = send(&app, "POST", "/books", Some(json!({"year": 2000}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        body["details"],
        json!(["title is required", "author is required"])
    );

    let (status, _) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "   ", "author": "Someone"})),
    )
    .await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    let (_, list) = send(&app, "GET", "/books", None).await;
    assert_eq!(list, json!([]));
}

#[tokio::test]
async fn malformed_json_returns_json_error() {
    let app = test_app();
    let request = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let response = app.oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let body: Value = serde_json::from_slice(&bytes).unwrap();
    assert!(body["error"].is_string());
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = test_app();
    send(&app, "POST", "/books", Some(dune())).await;
    send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Emma", "author": "Jane Austen", "year": 1815})),
    )
    .await;

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 2);

    let (status, filtered) = send(&app, "GET", "/books?author=Jane%20Austen", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 1);
    assert_eq!(filtered[0]["title"], "Emma");
    assert_eq!(filtered[0]["isbn"], Value::Null);

    let (_, none) = send(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(none, json!([]));
}

#[tokio::test]
async fn update_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, updated) = send(
        &app,
        "PUT",
        &uri,
        Some(json!({"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["year"], 1969);
    assert_eq!(updated["isbn"], Value::Null);

    let (status, _) = send(&app, "PUT", &uri, Some(json!({"title": "No author"}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    let (status, _) = send(&app, "PUT", "/books/999", Some(dune())).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, _) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, body) = send(&app, "GET", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");

    let (status, _) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}
