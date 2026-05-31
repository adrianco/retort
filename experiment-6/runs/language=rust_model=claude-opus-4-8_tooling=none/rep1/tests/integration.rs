use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_collection::app_in_memory;
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let request = Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json");

    let request = match body {
        Some(b) => request.body(Body::from(b.to_string())).unwrap(),
        None => request.body(Body::empty()).unwrap(),
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
    let app = app_in_memory();
    let (status, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = app_in_memory();

    let (status, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123" })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Herbert");
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["year"], 1965);
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = app_in_memory();

    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "", "author": "Nobody" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].is_string());

    let (status, _) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Lonely" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = app_in_memory();

    for (title, author) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        send(
            &app,
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
    }

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, alice) = send(&app, "GET", "/books?author=Alice", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(alice.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn update_book() {
    let app = app_in_memory();

    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Old", "author": "Author" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({ "title": "New", "author": "Author", "year": 2020 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["year"], 2020);

    let (status, _) = send(
        &app,
        "PUT",
        "/books/999999",
        Some(json!({ "title": "X", "author": "Y" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book() {
    let app = app_in_memory();

    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Temp", "author": "Author" })),
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
