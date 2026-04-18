use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use books_api::{build_app, init_db, Book};
use std::sync::{Arc, Mutex};
use tower::ServiceExt;

fn app() -> axum::Router {
    let conn = init_db(":memory:").unwrap();
    build_app(Arc::new(Mutex::new(conn)))
}

async fn body_json<T: serde::de::DeserializeOwned>(resp: axum::response::Response) -> T {
    let bytes = to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_ok() {
    let resp = app()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn create_and_get_book() {
    let app = app();
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let book: Book = body_json(resp).await;
    assert_eq!(book.title, "Dune");

    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", book.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched: Book = body_json(resp).await;
    assert_eq!(fetched, book);
}

#[tokio::test]
async fn create_missing_title_is_400() {
    let resp = app()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(r#"{"author":"X"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_filter_by_author_and_delete() {
    let app = app();
    for payload in [
        r#"{"title":"A","author":"Alice"}"#,
        r#"{"title":"B","author":"Bob"}"#,
        r#"{"title":"C","author":"Alice"}"#,
    ] {
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(payload))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let books: Vec<Book> = body_json(resp).await;
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "Alice"));

    let id = &books[0].id;
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
