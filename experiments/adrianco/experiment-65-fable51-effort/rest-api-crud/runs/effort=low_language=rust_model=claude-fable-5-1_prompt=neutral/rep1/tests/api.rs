use axum::{
    body::Body,
    http::{header, Request, StatusCode},
    Router,
};
use book_api::{app, db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(db::open(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            req = req.header(header::CONTENT_TYPE, "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let resp = app.clone().oneshot(req.body(body).unwrap()).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
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
        Some(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"})),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(body["title"], "Dune");
    let id = body["id"].as_i64().unwrap();

    let (status, body) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["author"], "Frank Herbert");
    assert_eq!(body["year"], 1965);
    assert_eq!(body["isbn"], "9780441013593");
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

    let (status, _) = send(&app, "POST", "/books", Some(json!({"title": "T", "author": "A", "isbn": "123"}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // malformed JSON body
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let resp = app.clone().oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_and_filter_by_author() {
    let app = test_app();
    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        let (status, _) = send(&app, "POST", "/books", Some(json!({"title": t, "author": a}))).await;
        assert_eq!(status, StatusCode::CREATED);
    }
    let (status, body) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    let (status, body) = send(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    let arr = body.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    assert!(arr.iter().all(|b| b["author"] == "Alice"));

    let (_, body) = send(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(body.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();
    let (_, body) = send(&app, "POST", "/books", Some(json!({"title": "Old", "author": "A"}))).await;
    let id = body["id"].as_i64().unwrap();

    let (status, body) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "New", "author": "B", "year": 2001})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "New");
    assert_eq!(body["author"], "B");
    assert_eq!(body["year"], 2001);
    assert!(body["isbn"].is_null());

    let (status, _) = send(&app, "PUT", &format!("/books/{id}"), Some(json!({"author": "B"}))).await;
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
