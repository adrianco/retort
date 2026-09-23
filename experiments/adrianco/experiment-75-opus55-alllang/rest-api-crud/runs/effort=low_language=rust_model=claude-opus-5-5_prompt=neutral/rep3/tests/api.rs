use axum::{body::Body, http::{Request, StatusCode}, Router};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn app() -> Router {
    books_api::app(books_api::open_db(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(b) => {
            req = req.header("content-type", "application/json");
            Body::from(b.to_string())
        }
        None => Body::empty(),
    };
    let resp = app.clone().oneshot(req.body(body).unwrap()).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let v = if bytes.is_empty() { Value::Null } else { serde_json::from_slice(&bytes).unwrap() };
    (status, v)
}

#[tokio::test]
async fn health_check() {
    let (s, v) = send(&app(), "GET", "/health", None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(v["status"], "ok");
}

#[tokio::test]
async fn crud_lifecycle() {
    let app = app();
    let (s, b) = send(&app, "POST", "/books",
        Some(json!({"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}))).await;
    assert_eq!(s, StatusCode::CREATED);
    let id = b["id"].as_i64().unwrap();

    let (s, b) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(b["title"], "Dune");

    let (s, b) = send(&app, "PUT", &format!("/books/{id}"),
        Some(json!({"title":"Dune Messiah","author":"Frank Herbert","year":1969}))).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(b["title"], "Dune Messiah");
    assert_eq!(b["year"], 1969);

    let (s, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NO_CONTENT);
    let (s, _) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
    let (s, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_requires_title_and_author() {
    let app = app();
    let (s, v) = send(&app, "POST", "/books", Some(json!({"title":"  ","year":2000}))).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    assert_eq!(v["details"].as_array().unwrap().len(), 2);

    let (_, b) = send(&app, "POST", "/books", Some(json!({"title":"A","author":"B"}))).await;
    let (s, _) = send(&app, "PUT", &format!("/books/{}", b["id"]), Some(json!({"title":"X"}))).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    let (s, _) = send(&app, "PUT", "/books/999", Some(json!({"title":"X","author":"Y"}))).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_with_author_filter() {
    let app = app();
    for (t, a) in [("Emma", "Jane Austen"), ("Persuasion", "Jane Austen"), ("Ulysses", "James Joyce")] {
        send(&app, "POST", "/books", Some(json!({"title":t,"author":a}))).await;
    }
    let (s, v) = send(&app, "GET", "/books", None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(v.as_array().unwrap().len(), 3);
    let (_, v) = send(&app, "GET", "/books?author=Jane%20Austen", None).await;
    assert_eq!(v.as_array().unwrap().len(), 2);
}
