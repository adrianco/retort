use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_api::{app, open_db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(open_db(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let req = Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(match body {
            Some(v) => Body::from(v.to_string()),
            None => Body::empty(),
        })
        .unwrap();
    let res = app.clone().oneshot(req).await.unwrap();
    let status = res.status();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, value)
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
    let (status, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"})),
    )
    .await;
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
    let (status, body) = send(&app, "POST", "/books", Some(json!({"author": "Anon"}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) = send(&app, "POST", "/books", Some(json!({"title": "Untitled"}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author is required");

    let (status, _) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "   ", "author": "Anon"})),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_with_author_filter() {
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
            Some(json!({"title": title, "author": author})),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) =
        send(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b["author"] == "Frank Herbert"));
}

#[tokio::test]
async fn update_book() {
    let app = test_app();
    let (_, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Draft", "author": "Anon"})),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "Final", "author": "Known Author", "year": 2024})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Final");
    assert_eq!(updated["author"], "Known Author");
    assert_eq!(updated["year"], 2024);

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
        Some(json!({"title": "Ephemeral", "author": "Anon"})),
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
