use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use book_collection::{app, open_db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

/// Build a router backed by a fresh in-memory database.
fn test_app() -> axum::Router {
    let db = open_db(":memory:").expect("open in-memory db");
    app(db)
}

async fn body_json(resp: axum::response::Response) -> Value {
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

fn post_book(body: Value) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

#[tokio::test]
async fn health_check_ok() {
    let app = test_app();
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
    let json = body_json(resp).await;
    assert_eq!(json["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();

    let resp = app
        .clone()
        .oneshot(post_book(json!({
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "9780441013593"
        })))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created = body_json(resp).await;
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    let id = created["id"].as_i64().unwrap();

    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched = body_json(resp).await;
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["title"], "Dune");
}

#[tokio::test]
async fn create_requires_title_and_author() {
    let app = test_app();

    let resp = app
        .clone()
        .oneshot(post_book(json!({ "author": "Nobody" })))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let json = body_json(resp).await;
    assert_eq!(json["error"], "title is required");

    let resp = app
        .oneshot(post_book(json!({ "title": "Untitled" })))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let json = body_json(resp).await;
    assert_eq!(json["error"], "author is required");
}

#[tokio::test]
async fn list_filters_by_author() {
    let app = test_app();

    for body in [
        json!({ "title": "A", "author": "Alice" }),
        json!({ "title": "B", "author": "Bob" }),
        json!({ "title": "C", "author": "Alice" }),
    ] {
        let resp = app.clone().oneshot(post_book(body)).await.unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let all = body_json(resp).await;
    assert_eq!(all.as_array().unwrap().len(), 3);

    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let filtered = body_json(resp).await;
    let arr = filtered.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    assert!(arr.iter().all(|b| b["author"] == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();

    let resp = app
        .clone()
        .oneshot(post_book(json!({ "title": "Old", "author": "Auth" })))
        .await
        .unwrap();
    let id = body_json(resp).await["id"].as_i64().unwrap();

    // Update
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({ "title": "New", "author": "Auth", "year": 2020 }).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated = body_json(resp).await;
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["year"], 2020);

    // Delete
    let resp = app
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
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Now it should be gone.
    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books/999")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
