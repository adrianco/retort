//! Integration tests that drive the Axum router directly (no sockets).

use axum::{
    body::Body,
    http::{header, Method, Request, StatusCode},
    Router,
};
use book_api::{app, models::Book, Db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(Db::in_memory().expect("open in-memory db"))
}

async fn send(app: &Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            builder = builder.header(header::CONTENT_TYPE, "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let req = builder.body(body).unwrap();
    let resp = app.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap_or(Value::Null)
    };
    (status, json)
}

async fn create(
    app: &Router,
    title: &str,
    author: &str,
    year: Option<i32>,
    isbn: Option<&str>,
) -> Book {
    let (status, body) = send(
        app,
        Method::POST,
        "/books",
        Some(json!({ "title": title, "author": author, "year": year, "isbn": isbn })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "unexpected body: {body}");
    serde_json::from_value(body).unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = send(&app, Method::GET, "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
    assert_eq!(body["database"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let book = create(
        &app,
        "Dune",
        "Frank Herbert",
        Some(1965),
        Some("9780441013593"),
    )
    .await;
    assert_eq!(book.title, "Dune");
    assert_eq!(book.author, "Frank Herbert");
    assert_eq!(book.year, Some(1965));
    assert_eq!(book.isbn.as_deref(), Some("9780441013593"));
    assert!(book.id > 0);

    let (status, body) = send(&app, Method::GET, &format!("/books/{}", book.id), None).await;
    assert_eq!(status, StatusCode::OK);
    let fetched: Book = serde_json::from_value(body).unwrap();
    assert_eq!(fetched, book);
}

#[tokio::test]
async fn create_requires_title_and_author() {
    let app = test_app();

    // Missing both required fields.
    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "year": 2000 }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "validation failed");
    let details = body["details"].as_array().unwrap();
    assert!(details.iter().any(|d| d == "title is required"));
    assert!(details.iter().any(|d| d == "author is required"));

    // Whitespace-only title is treated as missing.
    let (status, body) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "   ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["details"]
        .as_array()
        .unwrap()
        .iter()
        .any(|d| d == "title is required"));

    // Malformed JSON body.
    let req = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let resp = app.clone().oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Nothing was persisted.
    let (status, body) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = test_app();
    create(&app, "Dune", "Frank Herbert", Some(1965), None).await;
    create(&app, "Dune Messiah", "Frank Herbert", Some(1969), None).await;
    create(&app, "Neuromancer", "William Gibson", Some(1984), None).await;

    let (status, body) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    let (status, body) = send(&app, Method::GET, "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let books: Vec<Book> = serde_json::from_value(body).unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b.author == "Frank Herbert"));

    // Filter is case-insensitive.
    let (status, body) = send(&app, Method::GET, "/books?author=william%20gibson", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 1);

    // Unknown author yields an empty list, not an error.
    let (status, body) = send(&app, Method::GET, "/books?author=Nobody", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn update_book() {
    let app = test_app();
    let book = create(&app, "Nueromancer", "W. Gibson", None, None).await;

    let (status, body) = send(
        &app,
        Method::PUT,
        &format!("/books/{}", book.id),
        Some(json!({ "title": "Neuromancer", "author": "William Gibson", "year": 1984, "isbn": "0441569595" })),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "body: {body}");
    let updated: Book = serde_json::from_value(body).unwrap();
    assert_eq!(updated.id, book.id);
    assert_eq!(updated.title, "Neuromancer");
    assert_eq!(updated.author, "William Gibson");
    assert_eq!(updated.year, Some(1984));
    assert_eq!(updated.isbn.as_deref(), Some("0441569595"));

    // Persisted.
    let (_, body) = send(&app, Method::GET, &format!("/books/{}", book.id), None).await;
    assert_eq!(body["title"], "Neuromancer");

    // Validation applies to updates too.
    let (status, _) = send(
        &app,
        Method::PUT,
        &format!("/books/{}", book.id),
        Some(json!({ "title": "", "author": "William Gibson" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // Updating a missing book is 404.
    let (status, body) = send(
        &app,
        Method::PUT,
        "/books/9999",
        Some(json!({ "title": "X", "author": "Y" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
}

#[tokio::test]
async fn delete_book() {
    let app = test_app();
    let book = create(&app, "Snow Crash", "Neal Stephenson", Some(1992), None).await;

    let (status, body) = send(&app, Method::DELETE, &format!("/books/{}", book.id), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, _) = send(&app, Method::GET, &format!("/books/{}", book.id), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, Method::DELETE, &format!("/books/{}", book.id), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_and_invalid_ids() {
    let app = test_app();

    let (status, body) = send(&app, Method::GET, "/books/12345", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");

    // Non-numeric id is rejected by the path extractor.
    let (status, _) = send(&app, Method::GET, "/books/not-a-number", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn duplicate_isbn_is_conflict() {
    let app = test_app();
    create(
        &app,
        "Dune",
        "Frank Herbert",
        Some(1965),
        Some("9780441013593"),
    )
    .await;

    let (status, body) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Dune (reprint)", "author": "Frank Herbert", "isbn": "9780441013593" })),
    )
    .await;
    assert_eq!(status, StatusCode::CONFLICT);
    assert_eq!(body["error"], "a book with this isbn already exists");

    // Invalid ISBN length is a validation error.
    let (status, body) = send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Bad", "author": "Author", "isbn": "123" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["details"]
        .as_array()
        .unwrap()
        .iter()
        .any(|d| d.as_str().unwrap().starts_with("isbn must contain")));
}
