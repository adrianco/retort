use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use books_api::{app, AppState};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(AppState::open(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            req = req.header("content-type", "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let res = app.clone().oneshot(req.body(body).unwrap()).await.unwrap();
    let status = res.status();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("response body should be JSON")
    };
    (status, value)
}

fn dune() -> Value {
    json!({ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" })
}

#[tokio::test]
async fn health_check() {
    let (status, body) = send(&test_app(), "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
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
async fn optional_fields_may_be_omitted() {
    let app = test_app();
    let (status, created) =
        send(&app, "POST", "/books", Some(json!({ "title": "T", "author": "A" }))).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["year"], Value::Null);
    assert_eq!(created["isbn"], Value::Null);
}

#[tokio::test]
async fn create_requires_title_and_author() {
    let app = test_app();
    let (status, body) = send(&app, "POST", "/books", Some(json!({ "year": 2000 }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(
        body["details"],
        json!(["title is required", "author is required"])
    );

    // Blank strings count as missing.
    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "   ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["details"], json!(["title is required"]));

    let (_, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(all, json!([]));
}

#[tokio::test]
async fn malformed_body_is_a_json_400() {
    let app = test_app();
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let res = app.clone().oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let body: Value = serde_json::from_slice(&bytes).unwrap();
    assert!(body["error"].as_str().unwrap().contains("invalid JSON"));

    // Wrong type for a field.
    let (status, _) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "T", "author": "A", "year": "nineteen" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_and_filter_by_author() {
    let app = test_app();
    send(&app, "POST", "/books", Some(dune())).await;
    send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969 })),
    )
    .await;
    send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Emma", "author": "Jane Austen", "year": 1815 })),
    )
    .await;

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, herbert) = send(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let herbert = herbert.as_array().unwrap();
    assert_eq!(herbert.len(), 2);
    assert!(herbert.iter().all(|b| b["author"] == "Frank Herbert"));

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
        Some(json!({ "title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["id"], created["id"]);
    assert_eq!(updated["title"], "Dune (Revised)");
    assert_eq!(updated["year"], 1966);
    assert_eq!(updated["isbn"], Value::Null);

    let (_, fetched) = send(&app, "GET", &uri, None).await;
    assert_eq!(fetched, updated);

    // Validation applies to updates too, and leaves the record untouched.
    let (status, _) = send(&app, "PUT", &uri, Some(json!({ "title": "No author" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let (_, fetched) = send(&app, "GET", &uri, None).await;
    assert_eq!(fetched, updated);
}

#[tokio::test]
async fn delete_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, body) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, _) = send(&app, "GET", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn missing_and_invalid_ids() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");

    let (status, _) = send(&app, "PUT", "/books/999", Some(dune())).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, body) = send(&app, "GET", "/books/abc", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].is_string());
}
