//! Integration tests: exercise the full HTTP stack (router + handlers +
//! SQLite) against an in-memory database.

use std::sync::{Arc, Mutex};

use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::response::Response;
use book_api::{create_tables, router, AppState};
use http_body_util::BodyExt;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

fn app() -> axum::Router {
    let mut conn = Connection::open_in_memory().unwrap();
    create_tables(&mut conn).unwrap();
    router(AppState {
        db: Arc::new(Mutex::new(conn)),
    })
}

async fn body_json(res: Response) -> Value {
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    }
}

async fn post_book(app: axum::Router, body: Value) -> Response {
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap();
    app.oneshot(req).await.unwrap()
}

async fn create_sample_book(app: &axum::Router) -> i64 {
    let res = post_book(
        app.clone(),
        json!({"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-261-10240-4"}),
    )
    .await;
    assert_eq!(res.status(), StatusCode::CREATED);
    body_json(res).await["id"].as_i64().unwrap()
}

#[tokio::test]
async fn root_returns_service_info() {
    let app = app();
    let req = Request::builder().uri("/").body(Body::empty()).unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body = body_json(res).await;
    assert_eq!(body["service"], "book-api");
}

#[tokio::test]
async fn health_returns_ok() {
    let app = app();
    let req = Request::builder()
        .uri("/health")
        .body(Body::empty())
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    assert_eq!(body_json(res).await, json!({"status": "ok"}));
}

#[tokio::test]
async fn create_book_returns_201_with_id() {
    let app = app();
    let res = post_book(
        app,
        json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}),
    )
    .await;
    assert_eq!(res.status(), StatusCode::CREATED);
    let body = body_json(res).await;
    assert!(body["id"].as_i64().unwrap() > 0);
    assert_eq!(body["title"], "Dune");
    assert_eq!(body["author"], "Frank Herbert");
    assert_eq!(body["year"], 1965);
    assert_eq!(body["isbn"], "978-0-441-17271-9");
}

#[tokio::test]
async fn create_book_without_title_is_400() {
    let app = app();
    let res = post_book(app, json!({"author": "Someone"})).await;
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    let body = body_json(res).await;
    assert!(body["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn create_book_without_author_is_400() {
    let app = app();
    let res = post_book(app, json!({"title": "A Book"})).await;
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    let body = body_json(res).await;
    assert!(body["error"].as_str().unwrap().contains("author"));
}

#[tokio::test]
async fn create_book_with_blank_fields_is_400() {
    let app = app();
    let res = post_book(app, json!({"title": "   ", "author": "X"})).await;
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn create_book_with_bad_year_is_400() {
    let app = app();
    let res = post_book(
        app,
        json!({"title": "A Book", "author": "X", "year": 3000}),
    )
    .await;
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn create_book_with_malformed_json_is_400() {
    let app = app();
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_returns_all() {
    let app = app();
    create_sample_book(&app).await;
    post_book(app.clone(), json!({"title": "Neuromancer", "author": "William Gibson"}))
        .await;

    let req = Request::builder().uri("/books").body(Body::empty()).unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let books = body_json(res).await;
    assert_eq!(books.as_array().unwrap().len(), 2);
    assert_eq!(books[0]["title"], "The Hobbit");
    assert_eq!(books[1]["title"], "Neuromancer");
}

#[tokio::test]
async fn list_books_filters_by_author_case_insensitive() {
    let app = app();
    create_sample_book(&app).await;
    post_book(
        app.clone(),
        json!({"title": "The Silmarillion", "author": "j.r.r. tolkien"}),
    )
    .await;
    post_book(app.clone(), json!({"title": "Neuromancer", "author": "William Gibson"}))
        .await;

    let req = Request::builder()
        .uri("/books?author=J.R.R.%20Tolkien")
        .body(Body::empty())
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let books = body_json(res).await;
    let arr = books.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    assert!(arr.iter().all(|b| b["author"] == "j.r.r. tolkien" || b["author"] == "J.R.R. Tolkien"));
}

#[tokio::test]
async fn get_book_by_id() {
    let app = app();
    let id = create_sample_book(&app).await;

    let req = Request::builder()
        .uri(format!("/books/{id}"))
        .body(Body::empty())
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let book = body_json(res).await;
    assert_eq!(book["id"], id);
    assert_eq!(book["title"], "The Hobbit");
    assert_eq!(book["author"], "J.R.R. Tolkien");
    assert_eq!(book["year"], 1937);
}

#[tokio::test]
async fn get_missing_book_is_404() {
    let app = app();
    let req = Request::builder()
        .uri("/books/9999")
        .body(Body::empty())
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = app();
    let id = create_sample_book(&app).await;

    let req = Request::builder()
        .method("PUT")
        .uri(format!("/books/{id}"))
        .header("content-type", "application/json")
        .body(Body::from(
            json!({"title": "The Hobbit (Revised)", "author": "J.R.R. Tolkien", "year": 1951})
                .to_string(),
        ))
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let book = body_json(res).await;
    assert_eq!(book["title"], "The Hobbit (Revised)");
    assert_eq!(book["year"], 1951);
    assert_eq!(book["isbn"], Value::Null); // isbn omitted -> cleared
}

#[tokio::test]
async fn update_missing_book_is_404() {
    let app = app();
    let req = Request::builder()
        .method("PUT")
        .uri("/books/9999")
        .header("content-type", "application/json")
        .body(Body::from(json!({"title": "X", "author": "Y"}).to_string()))
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_book_with_invalid_payload_is_400() {
    let app = app();
    let id = create_sample_book(&app).await;
    let req = Request::builder()
        .method("PUT")
        .uri(format!("/books/{id}"))
        .header("content-type", "application/json")
        .body(Body::from(json!({"author": "Y"}).to_string()))
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn delete_book_removes_it() {
    let app = app();
    let id = create_sample_book(&app).await;

    let req = Request::builder()
        .method("DELETE")
        .uri(format!("/books/{id}"))
        .body(Body::empty())
        .unwrap();
    let res = app.clone().oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::NO_CONTENT);

    // Gone afterwards.
    let req = Request::builder()
        .uri(format!("/books/{id}"))
        .body(Body::empty())
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_missing_book_is_404() {
    let app = app();
    let req = Request::builder()
        .method("DELETE")
        .uri("/books/9999")
        .body(Body::empty())
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}
