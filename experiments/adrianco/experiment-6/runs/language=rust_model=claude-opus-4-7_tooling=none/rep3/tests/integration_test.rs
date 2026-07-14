use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use books_api::{app, db};

fn build_app() -> axum::Router {
    let db = db::init(":memory:").expect("init in-memory db");
    app(db)
}

async fn body_json(resp: axum::response::Response) -> Value {
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_returns_ok() {
    let app = build_app();
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let v = body_json(resp).await;
    assert_eq!(v["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = build_app();

    let payload = json!({
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik",
        "year": 2019,
        "isbn": "978-1718500440"
    });
    let resp = app
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
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created = body_json(resp).await;
    let id = created["id"].as_str().unwrap().to_string();
    assert_eq!(created["title"], "The Rust Programming Language");
    assert_eq!(created["author"], "Steve Klabnik");

    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched = body_json(resp).await;
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["year"], 2019);
}

#[tokio::test]
async fn create_missing_title_returns_400() {
    let app = build_app();
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(json!({"author": "Someone"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let v = body_json(resp).await;
    assert!(v["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_filter_by_author() {
    let app = build_app();

    for (title, author) in [
        ("Book A", "Alice"),
        ("Book B", "Bob"),
        ("Book C", "Alice"),
    ] {
        app.clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        json!({"title": title, "author": author}).to_string(),
                    ))
                    .unwrap(),
            )
            .await
            .unwrap();
    }

    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let v = body_json(resp).await;
    let arr = v.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    assert!(arr.iter().all(|b| b["author"] == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = build_app();

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"title": "Old", "author": "Author"}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    let created = body_json(resp).await;
    let id = created["id"].as_str().unwrap().to_string();

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", id))
                .header("content-type", "application/json")
                .body(Body::from(json!({"title": "New"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated = body_json(resp).await;
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["author"], "Author");

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_nonexistent_returns_404() {
    let app = build_app();
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books/does-not-exist")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
