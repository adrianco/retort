use axum::{
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use books_api::{app, db};
use serde_json::{json, Value};
use tower::ServiceExt;

async fn setup_app() -> axum::Router {
    let pool = db::init("sqlite::memory:")
        .await
        .expect("failed to init in-memory db");
    app(pool)
}

async fn body_to_json(body: Body) -> Value {
    let bytes = to_bytes(body, usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = setup_app().await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let json = body_to_json(response.into_body()).await;
    assert_eq!(json["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = setup_app().await;

    let payload = json!({
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik",
        "year": 2019,
        "isbn": "978-1718500440"
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
    let created = body_to_json(response.into_body()).await;
    let id = created["id"].as_str().unwrap().to_string();
    assert_eq!(created["title"], "The Rust Programming Language");
    assert_eq!(created["author"], "Steve Klabnik");

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let fetched = body_to_json(response.into_body()).await;
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["year"], 2019);
}

#[tokio::test]
async fn create_book_missing_title_returns_400() {
    let app = setup_app().await;

    let payload = json!({ "author": "Someone" });

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
    let json = body_to_json(response.into_body()).await;
    assert!(json["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_books_filters_by_author() {
    let app = setup_app().await;

    for (title, author) in [
        ("Book A", "Alice"),
        ("Book B", "Alice"),
        ("Book C", "Bob"),
    ] {
        let payload = json!({ "title": title, "author": author });
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
    }

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let json = body_to_json(response.into_body()).await;
    let arr = json.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    for b in arr {
        assert_eq!(b["author"], "Alice");
    }

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let json = body_to_json(response.into_body()).await;
    assert_eq!(json.as_array().unwrap().len(), 3);
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = setup_app().await;

    let payload = json!({ "title": "Original", "author": "Author" });
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
    let created = body_to_json(response.into_body()).await;
    let id = created["id"].as_str().unwrap().to_string();

    let update = json!({ "title": "Updated", "year": 2024 });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", id))
                .header("content-type", "application/json")
                .body(Body::from(update.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let updated = body_to_json(response.into_body()).await;
    assert_eq!(updated["title"], "Updated");
    assert_eq!(updated["author"], "Author");
    assert_eq!(updated["year"], 2024);

    let response = app
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
    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
