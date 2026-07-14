use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::{app, init_pool, Book};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

async fn test_app() -> axum::Router {
    let pool = init_pool("sqlite::memory:").await.unwrap();
    app(pool)
}

async fn send(app: &axum::Router, req: Request<Body>) -> (StatusCode, Value) {
    let resp = app.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let value: Value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, value)
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
async fn health_check_returns_ok() {
    let app = test_app().await;
    let req = Request::builder()
        .uri("/health")
        .body(Body::empty())
        .unwrap();
    let (status, body) = send(&app, req).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app().await;

    let (status, created) = send(
        &app,
        post_book(json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "9781593278281"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let book: Book = serde_json::from_value(created).unwrap();
    assert_eq!(book.title, "The Rust Programming Language");
    assert_eq!(book.year, Some(2018));

    let req = Request::builder()
        .uri(format!("/books/{}", book.id))
        .body(Body::empty())
        .unwrap();
    let (status, fetched) = send(&app, req).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched["author"], "Steve Klabnik");
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = test_app().await;

    let (status, body) = send(&app, post_book(json!({ "author": "Nobody" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));

    let (status, body) = send(&app, post_book(json!({ "title": "  " }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_with_author_filter() {
    let app = test_app().await;
    send(&app, post_book(json!({ "title": "A", "author": "Alice" }))).await;
    send(&app, post_book(json!({ "title": "B", "author": "Bob" }))).await;
    send(&app, post_book(json!({ "title": "C", "author": "Alice" }))).await;

    let req = Request::builder()
        .uri("/books?author=Alice")
        .body(Body::empty())
        .unwrap();
    let (status, body) = send(&app, req).await;
    assert_eq!(status, StatusCode::OK);
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app().await;
    let (_, created) = send(
        &app,
        post_book(json!({ "title": "Old", "author": "Writer" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    // Update
    let req = Request::builder()
        .method("PUT")
        .uri(format!("/books/{id}"))
        .header("content-type", "application/json")
        .body(Body::from(
            json!({ "title": "New", "author": "Writer", "year": 2020 }).to_string(),
        ))
        .unwrap();
    let (status, body) = send(&app, req).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "New");
    assert_eq!(body["year"], 2020);

    // Delete
    let req = Request::builder()
        .method("DELETE")
        .uri(format!("/books/{id}"))
        .body(Body::empty())
        .unwrap();
    let (status, _) = send(&app, req).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    // Now gone
    let req = Request::builder()
        .uri(format!("/books/{id}"))
        .body(Body::empty())
        .unwrap();
    let (status, _) = send(&app, req).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}
