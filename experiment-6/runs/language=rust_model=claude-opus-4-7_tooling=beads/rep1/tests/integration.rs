use axum::{
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use books_api::{build_router, new_in_memory_state, models::Book};
use serde_json::{json, Value};
use tower::ServiceExt;

async fn body_json(body: Body) -> Value {
    let bytes = to_bytes(body, 1024 * 1024).await.unwrap();
    if bytes.is_empty() {
        return Value::Null;
    }
    serde_json::from_slice(&bytes).unwrap()
}

fn app() -> axum::Router {
    build_router(new_in_memory_state())
}

#[tokio::test]
async fn health_returns_ok() {
    let response = app()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let v = body_json(response.into_body()).await;
    assert_eq!(v["status"], "ok");
}

#[tokio::test]
async fn create_get_and_list_book() {
    let router = app();

    let create_body = json!({
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik",
        "year": 2019,
        "isbn": "978-1718500440"
    })
    .to_string();

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(create_body))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);
    let created: Book = serde_json::from_value(body_json(response.into_body()).await).unwrap();
    assert_eq!(created.title, "The Rust Programming Language");
    assert_eq!(created.author, "Steve Klabnik");
    assert_eq!(created.year, Some(2019));
    assert!(created.id > 0);

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let fetched: Book = serde_json::from_value(body_json(response.into_body()).await).unwrap();
    assert_eq!(fetched, created);

    let response = router
        .clone()
        .oneshot(Request::builder().uri("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let list: Vec<Book> = serde_json::from_value(body_json(response.into_body()).await).unwrap();
    assert_eq!(list.len(), 1);
}

#[tokio::test]
async fn create_without_title_returns_400() {
    let response = app()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({ "author": "Someone" }).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let v = body_json(response.into_body()).await;
    assert_eq!(v["error"], "title is required");
}

#[tokio::test]
async fn create_without_author_returns_400() {
    let response = app()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({ "title": "Untitled" }).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn update_and_delete_book() {
    let router = app();

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({ "title": "Old", "author": "Author" }).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    let created: Book = serde_json::from_value(body_json(response.into_body()).await).unwrap();

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", created.id))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "title": "New Title",
                        "author": "New Author",
                        "year": 2024
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let updated: Book = serde_json::from_value(body_json(response.into_body()).await).unwrap();
    assert_eq!(updated.title, "New Title");
    assert_eq!(updated.author, "New Author");
    assert_eq!(updated.year, Some(2024));

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_filters_by_author() {
    let router = app();

    for payload in [
        json!({"title": "A", "author": "Alice"}),
        json!({"title": "B", "author": "Bob"}),
        json!({"title": "C", "author": "Alice"}),
    ] {
        let response = router
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

    let response = router
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
    let list: Vec<Book> = serde_json::from_value(body_json(response.into_body()).await).unwrap();
    assert_eq!(list.len(), 2);
    assert!(list.iter().all(|b| b.author == "Alice"));
}

#[tokio::test]
async fn get_missing_returns_404() {
    let response = app()
        .oneshot(
            Request::builder()
                .uri("/books/9999")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
