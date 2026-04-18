use axum::body::Body;
use axum::http::{Request, StatusCode};
use books_api::{app, init_db, Book};
use http_body_util::BodyExt;
use std::sync::{Arc, Mutex};
use tower::ServiceExt;

fn make_app() -> axum::Router {
    let conn = init_db(":memory:").unwrap();
    app(Arc::new(Mutex::new(conn)))
}

async fn body_json<T: serde::de::DeserializeOwned>(resp: axum::response::Response) -> T {
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_returns_ok() {
    let app = make_app();
    let resp = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn create_and_get_book() {
    let app = make_app();
    let payload = serde_json::json!({
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441013593"
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
    let got: Book = body_json(resp).await;
    assert_eq!(got, book);
}

#[tokio::test]
async fn create_without_title_rejected() {
    let app = make_app();
    let payload = serde_json::json!({ "author": "X" });
    let resp = app
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
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_filter_by_author_and_update_delete() {
    let app = make_app();
    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        let payload = serde_json::json!({ "title": t, "author": a });
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
    let books: Vec<Book> = body_json(resp).await;
    assert_eq!(books.len(), 2);
    let id = books[0].id.clone();

    let update = serde_json::json!({ "title": "A2", "author": "Alice", "year": 2000 });
    let resp = app
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
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: Book = body_json(resp).await;
    assert_eq!(updated.title, "A2");
    assert_eq!(updated.year, Some(2000));

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
