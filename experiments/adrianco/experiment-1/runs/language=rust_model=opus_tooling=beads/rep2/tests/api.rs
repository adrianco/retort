use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use books_api::{build_app, init_db, Book};
use tokio_rusqlite::Connection;
use tower::ServiceExt;

async fn app() -> axum::Router {
    let conn = Connection::open_in_memory().await.unwrap();
    init_db(&conn).await.unwrap();
    build_app(conn).await
}

async fn body_json(body: Body) -> serde_json::Value {
    let bytes = to_bytes(body, usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_ok() {
    let app = app().await;
    let res = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
}

#[tokio::test]
async fn create_and_get_book() {
    let app = app().await;
    let payload = serde_json::json!({
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719"
    });
    let res = app
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
    assert_eq!(res.status(), StatusCode::CREATED);
    let created: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(created.title, "Dune");

    let res = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let got: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(got.id, created.id);
    assert_eq!(got.author, "Frank Herbert");
}

#[tokio::test]
async fn create_missing_title_fails() {
    let app = app().await;
    let payload = serde_json::json!({ "author": "Nobody" });
    let res = app
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
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_filter_by_author() {
    let app = app().await;
    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        let payload = serde_json::json!({ "title": t, "author": a });
        let res = app
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
        assert_eq!(res.status(), StatusCode::CREATED);
    }
    let res = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let books: Vec<Book> = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "Alice"));
}

#[tokio::test]
async fn update_and_delete() {
    let app = app().await;
    let payload = serde_json::json!({ "title": "Old", "author": "X" });
    let res = app
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
    let created: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();

    let upd = serde_json::json!({ "title": "New", "author": "Y", "year": 2020 });
    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", created.id))
                .header("content-type", "application/json")
                .body(Body::from(upd.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let updated: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(updated.title, "New");
    assert_eq!(updated.year, Some(2020));

    let res = app
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
    assert_eq!(res.status(), StatusCode::NO_CONTENT);

    let res = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}
