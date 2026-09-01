use axum::{
    body::Body,
    http::{header, Request, StatusCode},
    Router,
};
use books_api::{app, db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(db::open_in_memory().expect("in-memory db"))
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
async fn health_returns_ok() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let payload = json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"});
    let (status, created) = send(&app, "POST", "/books", Some(payload)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn validation_rejects_missing_fields() {
    let app = test_app();
    let (status, body) = send(&app, "POST", "/books", Some(json!({"year": 2000}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    let details = body["details"].as_array().unwrap();
    assert!(details.iter().any(|d| d == "title is required"));
    assert!(details.iter().any(|d| d == "author is required"));

    // Blank strings count as missing.
    let (status, _) = send(&app, "POST", "/books", Some(json!({"title": "  ", "author": "x"}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    // Malformed JSON is a 400.
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
        let (s, _) = send(&app, "POST", "/books", Some(json!({"title": t, "author": a}))).await;
        assert_eq!(s, StatusCode::CREATED);
    }
    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, alice) = send(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    let alice = alice.as_array().unwrap();
    assert_eq!(alice.len(), 2);
    assert!(alice.iter().all(|b| b["author"] == "Alice"));

    let (_, none) = send(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(none.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(json!({"title": "Old", "author": "X"}))).await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "New", "author": "Y", "year": 2020})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["id"], id);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["author"], "Y");
    assert_eq!(updated["year"], 2020);
    assert_eq!(updated["isbn"], Value::Null);

    // Update validation still applies.
    let (status, _) = send(&app, "PUT", &format!("/books/{id}"), Some(json!({"title": "Only"}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn unknown_id_returns_404() {
    let app = test_app();
    let (s, body) = send(&app, "GET", "/books/999", None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
    let (s, _) = send(&app, "PUT", "/books/999", Some(json!({"title": "T", "author": "A"}))).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
    let (s, _) = send(&app, "DELETE", "/books/999", None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}
