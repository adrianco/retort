use std::sync::{Arc, Mutex};

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use book_api::{build_router, db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_router() -> axum::Router {
    let conn = rusqlite::Connection::open_in_memory().expect("open in-memory db");
    db::init_schema(&conn).expect("init schema");
    build_router(Arc::new(Mutex::new(conn)))
}

async fn body_json(response: axum::response::Response) -> Value {
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_router();

    let response = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_then_get_book() {
    let app = test_router();

    let payload = json!({
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "978-0345339683"
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);
    let created = body_json(response).await;
    let id = created["id"].as_i64().unwrap();
    assert_eq!(created["title"], "The Hobbit");

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let fetched = body_json(response).await;
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["author"], "J.R.R. Tolkien");
}

#[tokio::test]
async fn create_book_missing_fields_returns_400() {
    let app = test_router();

    let payload = json!({ "year": 2020 });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let body = body_json(response).await;
    assert!(body["error"].as_str().unwrap().contains("required"));
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_router();

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books/999")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_books_filters_by_author() {
    let app = test_router();

    for (title, author) in [
        ("Book A", "Author One"),
        ("Book B", "Author Two"),
        ("Book C", "Author One"),
    ] {
        let payload = json!({ "title": title, "author": author });
        let response = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);
    }

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let all = body_json(response).await;
    assert_eq!(all.as_array().unwrap().len(), 3);

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Author%20One")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let filtered = body_json(response).await;
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b["author"] == "Author One"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_router();

    let payload = json!({ "title": "Old Title", "author": "Old Author" });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let created = body_json(response).await;
    let id = created["id"].as_i64().unwrap();

    let update_payload = json!({ "title": "New Title", "author": "New Author", "year": 2024 });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(update_payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let updated = body_json(response).await;
    assert_eq!(updated["title"], "New Title");
    assert_eq!(updated["year"], 2024);

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_missing_book_returns_404() {
    let app = test_router();

    let payload = json!({ "title": "Title", "author": "Author" });
    let response = app
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/books/12345")
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
