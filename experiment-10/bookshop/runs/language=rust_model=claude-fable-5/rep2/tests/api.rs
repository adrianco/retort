use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use http_body_util::BodyExt;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    books_api::app(Connection::open_in_memory().unwrap())
}

async fn request(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
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

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = request(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let (status, created) = request(
        &app,
        "POST",
        "/books",
        Some(json!({
            "title": "The Phoenix Project",
            "author": "Gene Kim",
            "year": 2013,
            "isbn": "978-0988262591"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "The Phoenix Project");
    assert_eq!(created["author"], "Gene Kim");
    assert_eq!(created["year"], 2013);
    assert_eq!(created["isbn"], "978-0988262591");

    let id = created["id"].as_i64().unwrap();
    let (status, fetched) = request(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_rejects_missing_required_fields() {
    let app = test_app();
    let (status, body) = request(&app, "POST", "/books", Some(json!({ "year": 2020 }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let details = body["details"].as_array().unwrap();
    assert!(details.contains(&json!("title is required")));
    assert!(details.contains(&json!("author is required")));

    // Whitespace-only values are also rejected.
    let (status, _) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "  ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = test_app();
    for (title, author) in [
        ("Dune", "Frank Herbert"),
        ("Dune Messiah", "Frank Herbert"),
        ("Neuromancer", "William Gibson"),
    ] {
        let (status, _) = request(
            &app,
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = request(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) =
        request(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b["author"] == "Frank Herbert"));
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    let (_, created) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Drafty Title", "author": "A. Author" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = request(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({
            "title": "Final Title",
            "author": "A. Author",
            "year": 1999,
            "isbn": "123-456"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Final Title");
    assert_eq!(updated["year"], 1999);

    // Update with invalid payload is rejected.
    let (status, _) = request(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({ "title": "", "author": "" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // Update of a missing book is a 404.
    let (status, _) = request(
        &app,
        "PUT",
        "/books/99999",
        Some(json!({ "title": "X", "author": "Y" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book_removes_it() {
    let app = test_app();
    let (_, created) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Ephemeral", "author": "Nobody" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = request(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = request(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = request(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let (status, body) = request(&app, "GET", "/books/42", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}
