use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_api::app;
use http_body_util::BodyExt;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt;

fn router() -> Router {
    app(Connection::open_in_memory().unwrap())
}

async fn send(router: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            builder = builder.header("content-type", "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let resp = router
        .clone()
        .oneshot(builder.body(body).unwrap())
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap_or(Value::Null)
    };
    (status, json)
}

#[tokio::test]
async fn health_reports_ok() {
    let (status, body) = send(&router(), "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_then_get_book() {
    let r = router();
    let (status, created) = send(
        &r,
        "POST",
        "/books",
        Some(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"})),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let id = created["id"].as_i64().unwrap();
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["year"], 1965);

    let (status, fetched) = send(&r, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_rejects_missing_required_fields() {
    let r = router();
    let (status, body) = send(&r, "POST", "/books", Some(json!({"year": 2000}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    let details = body["details"].as_array().unwrap();
    assert!(details.contains(&json!("title is required")));
    assert!(details.contains(&json!("author is required")));
}

#[tokio::test]
async fn create_rejects_malformed_json() {
    let r = router();
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let resp = r.clone().oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_filters_by_author() {
    let r = router();
    send(&r, "POST", "/books", Some(json!({"title": "A", "author": "Asimov"}))).await;
    send(&r, "POST", "/books", Some(json!({"title": "B", "author": "Herbert"}))).await;

    let (_, all) = send(&r, "GET", "/books", None).await;
    assert_eq!(all.as_array().unwrap().len(), 2);

    let (status, filtered) = send(&r, "GET", "/books?author=asimov", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 1);
    assert_eq!(filtered[0]["title"], "A");
}

#[tokio::test]
async fn update_replaces_book() {
    let r = router();
    let (_, created) = send(&r, "POST", "/books", Some(json!({"title": "Old", "author": "X"}))).await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &r,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "New", "author": "Y", "year": 2001})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["author"], "Y");
    assert_eq!(updated["year"], 2001);
}

#[tokio::test]
async fn update_validates_input() {
    let r = router();
    let (_, created) = send(&r, "POST", "/books", Some(json!({"title": "T", "author": "A"}))).await;
    let id = created["id"].as_i64().unwrap();
    let (status, _) = send(&r, "PUT", &format!("/books/{id}"), Some(json!({"title": ""}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn delete_removes_book() {
    let r = router();
    let (_, created) = send(&r, "POST", "/books", Some(json!({"title": "T", "author": "A"}))).await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = send(&r, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(&r, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = send(&r, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn missing_book_returns_404_for_get_and_put() {
    let r = router();
    let (status, body) = send(&r, "GET", "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");

    let (status, _) = send(&r, "PUT", "/books/999", Some(json!({"title": "T", "author": "A"}))).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}
