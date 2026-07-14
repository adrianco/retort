use axum::{
    body::Body,
    http::{Request, StatusCode},
};
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
async fn health_works() {
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
    let created: Book = body_json(resp).await;
    assert_eq!(created.title, "Dune");

    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let got: Book = body_json(resp).await;
    assert_eq!(got.id, created.id);
    assert_eq!(got.author, "Frank Herbert");
}

#[tokio::test]
async fn create_book_requires_title() {
    let app = make_app();
    let payload = serde_json::json!({"author": "Someone"});
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
async fn update_and_delete_book() {
    let app = make_app();
    let create = serde_json::json!({"title": "A", "author": "B"});
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(create.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let created: Book = body_json(resp).await;

    let update = serde_json::json!({"title": "A2", "author": "B2", "year": 2020});
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", created.id))
                .header("content-type", "application/json")
                .body(Body::from(update.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: Book = body_json(resp).await;
    assert_eq!(updated.title, "A2");
    assert_eq!(updated.year, Some(2020));

    let resp = app
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
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let resp = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_books_filter_by_author() {
    let app = make_app();
    for (t, a) in [("t1", "alice"), ("t2", "bob"), ("t3", "alice")] {
        let payload = serde_json::json!({"title": t, "author": a});
        app.clone()
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
    }
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books?author=alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let books: Vec<Book> = body_json(resp).await;
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "alice"));
}
