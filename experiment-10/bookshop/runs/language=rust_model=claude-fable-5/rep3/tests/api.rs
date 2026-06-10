use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::util::ServiceExt;

fn test_app() -> Router {
    book_api::app(book_api::new_db(None).expect("in-memory db"))
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let request = match body {
        Some(json) => Request::builder()
            .method(method)
            .uri(uri)
            .header("content-type", "application/json")
            .body(Body::from(json.to_string()))
            .unwrap(),
        None => Request::builder()
            .method(method)
            .uri(uri)
            .body(Body::empty())
            .unwrap(),
    };
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, json)
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
        Some(json!({
            "title": "The Pragmatic Programmer",
            "author": "Hunt & Thomas",
            "year": 1999,
            "isbn": "978-0201616224"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "The Pragmatic Programmer");
    assert_eq!(created["author"], "Hunt & Thomas");
    assert_eq!(created["year"], 1999);
    assert_eq!(created["isbn"], "978-0201616224");
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_rejects_missing_required_fields() {
    let app = test_app();

    let (status, body) = send(&app, "POST", "/books", Some(json!({ "author": "Anon" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Untitled", "author": "   " })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author is required");
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = test_app();
    for (title, author) in [
        ("Dune", "Frank Herbert"),
        ("Dune Messiah", "Frank Herbert"),
        ("Neuromancer", "William Gibson"),
    ] {
        let (status, _) = send(
            &app,
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) = send(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b["author"] == "Frank Herbert"));
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Drafty Title", "author": "A. Writer" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({
            "title": "Final Title",
            "author": "A. Writer",
            "year": 2024
        })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Final Title");
    assert_eq!(updated["year"], 2024);

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, updated);

    let (status, body) = send(
        &app,
        "PUT",
        "/books/9999",
        Some(json!({ "title": "Ghost", "author": "Nobody" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}

#[tokio::test]
async fn delete_book_then_404() {
    let app = test_app();
    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Ephemeral", "author": "Gone Soon" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/books/42", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}
