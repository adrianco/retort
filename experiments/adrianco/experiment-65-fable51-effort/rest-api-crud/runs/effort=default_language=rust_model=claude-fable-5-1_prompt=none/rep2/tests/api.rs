//! Integration tests that exercise the full router against an in-memory SQLite database.

use axum::{
    body::Body,
    http::{header, Method, Request, StatusCode},
    Router,
};
use books_api::{app, db, AppState};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    let conn = db::open(":memory:").expect("open in-memory db");
    app(AppState::new(conn))
}

async fn send(app: &Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            req = req.header(header::CONTENT_TYPE, "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let resp = app
        .clone()
        .oneshot(req.body(body).unwrap())
        .await
        .expect("request failed");
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("response is not JSON")
    };
    (status, json)
}

#[tokio::test]
async fn health_returns_ok() {
    let app = test_app();
    let (status, body) = send(&app, Method::GET, "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_then_get_book() {
    let app = test_app();
    let payload = json!({
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0441478125"
    });
    let (status, created) = send(&app, Method::POST, "/books", Some(payload)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["id"], 1);
    assert_eq!(created["title"], "The Left Hand of Darkness");
    assert_eq!(created["author"], "Ursula K. Le Guin");
    assert_eq!(created["year"], 1969);
    assert_eq!(created["isbn"], "978-0441478125");

    let (status, fetched) = send(&app, Method::GET, "/books/1", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_rejects_missing_required_fields() {
    let app = test_app();

    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "year": 2001 }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let details = body["details"].as_array().expect("details array");
    assert!(details.iter().any(|d| d == "title is required"));
    assert!(details.iter().any(|d| d == "author is required"));

    // Blank strings count as missing.
    let (status, _) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "   ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // Malformed JSON is a 400, not a 422/415.
    let req = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let resp = app.clone().oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Nothing was persisted.
    let (_, list) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(list, json!([]));
}

#[tokio::test]
async fn list_supports_author_filter() {
    let app = test_app();
    for (title, author) in [
        ("Kindred", "Octavia Butler"),
        ("Parable of the Sower", "Octavia Butler"),
        ("Neuromancer", "William Gibson"),
    ] {
        let (status, _) = send(
            &app,
            Method::POST,
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) = send(&app, Method::GET, "/books?author=Octavia%20Butler", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b["author"] == "Octavia Butler"));

    let (status, none) = send(&app, Method::GET, "/books?author=Nobody", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(none, json!([]));
}

#[tokio::test]
async fn update_replaces_fields_and_validates() {
    let app = test_app();
    let (_, created) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Draft", "author": "Anon", "year": 1999 })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = send(
        &app,
        Method::PUT,
        &format!("/books/{id}"),
        Some(json!({ "title": "Final", "author": "Known Author", "isbn": "123" })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Final");
    assert_eq!(updated["author"], "Known Author");
    assert_eq!(updated["isbn"], "123");
    assert!(updated.get("year").is_none(), "PUT replaces omitted fields");

    let (status, _) = send(
        &app,
        Method::PUT,
        &format!("/books/{id}"),
        Some(json!({ "title": "", "author": "X" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let (status, body) = send(
        &app,
        Method::PUT,
        "/books/9999",
        Some(json!({ "title": "Ghost", "author": "Nobody" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}

#[tokio::test]
async fn delete_removes_book_and_missing_ids_are_404() {
    let app = test_app();
    let (_, created) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Ephemeral", "author": "Gone Soon" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, body) = send(&app, Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, _) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, Method::GET, "/books/not-a-number", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn duplicate_isbn_returns_conflict() {
    let app = test_app();
    let payload = json!({ "title": "One", "author": "A", "isbn": "dup-1" });
    let (status, _) = send(&app, Method::POST, "/books", Some(payload.clone())).await;
    assert_eq!(status, StatusCode::CREATED);
    let (status, body) = send(&app, Method::POST, "/books", Some(payload)).await;
    assert_eq!(status, StatusCode::CONFLICT);
    assert_eq!(body["error"], "a book with this isbn already exists");
}
