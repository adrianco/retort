use std::sync::Arc;

use axum::{
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use book_api::{app, db::Db, models::Book};
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> axum::Router {
    let db = Arc::new(Db::new(":memory:").unwrap());
    app(db)
}

async fn body_json(resp: axum::response::Response) -> Value {
    let bytes = to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    if bytes.is_empty() {
        return Value::Null;
    }
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_returns_ok() {
    let app = test_app();
    let resp = app
        .oneshot(Request::get("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_json(resp).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let create = Request::post("/books")
        .header("content-type", "application/json")
        .body(Body::from(
            json!({
                "title": "Dune",
                "author": "Frank Herbert",
                "year": 1965,
                "isbn": "9780441013593"
            })
            .to_string(),
        ))
        .unwrap();
    let resp = app.clone().oneshot(create).await.unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created: Book = serde_json::from_value(body_json(resp).await).unwrap();
    assert_eq!(created.title, "Dune");
    assert_eq!(created.author, "Frank Herbert");
    assert_eq!(created.year, Some(1965));

    let get = Request::get(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();
    let resp = app.oneshot(get).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched: Book = serde_json::from_value(body_json(resp).await).unwrap();
    assert_eq!(fetched.id, created.id);
    assert_eq!(fetched.title, "Dune");
}

#[tokio::test]
async fn create_missing_title_returns_400() {
    let app = test_app();
    let req = Request::post("/books")
        .header("content-type", "application/json")
        .body(Body::from(
            json!({"author": "Someone"}).to_string(),
        ))
        .unwrap();
    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let body = body_json(resp).await;
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_filters_by_author() {
    let app = test_app();
    for (title, author) in [
        ("Book One", "Alice"),
        ("Book Two", "Bob"),
        ("Book Three", "Alice"),
    ] {
        let req = Request::post("/books")
            .header("content-type", "application/json")
            .body(Body::from(
                json!({"title": title, "author": author}).to_string(),
            ))
            .unwrap();
        let resp = app.clone().oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

    let resp = app
        .clone()
        .oneshot(
            Request::get("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let books: Vec<Book> = serde_json::from_value(body_json(resp).await).unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "Alice"));

    let resp = app
        .oneshot(Request::get("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let all: Vec<Book> = serde_json::from_value(body_json(resp).await).unwrap();
    assert_eq!(all.len(), 3);
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();
    let create = Request::post("/books")
        .header("content-type", "application/json")
        .body(Body::from(
            json!({"title": "Old Title", "author": "Old Author"}).to_string(),
        ))
        .unwrap();
    let resp = app.clone().oneshot(create).await.unwrap();
    let created: Book = serde_json::from_value(body_json(resp).await).unwrap();

    let update = Request::put(format!("/books/{}", created.id))
        .header("content-type", "application/json")
        .body(Body::from(
            json!({"title": "New Title", "author": "New Author", "year": 2020}).to_string(),
        ))
        .unwrap();
    let resp = app.clone().oneshot(update).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: Book = serde_json::from_value(body_json(resp).await).unwrap();
    assert_eq!(updated.title, "New Title");
    assert_eq!(updated.year, Some(2020));

    let del = Request::delete(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();
    let resp = app.clone().oneshot(del).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let get = Request::get(format!("/books/{}", created.id))
        .body(Body::empty())
        .unwrap();
    let resp = app.oneshot(get).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_returns_404() {
    let app = test_app();
    let resp = app
        .oneshot(
            Request::get("/books/does-not-exist")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
