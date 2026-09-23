use axum::{body::Body, http::{Request, StatusCode}, Router};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn app() -> Router {
    books_api::app(books_api::open_db(":memory:").unwrap())
}

async fn call(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(b) => {
            req = req.header("content-type", "application/json");
            Body::from(b.to_string())
        }
        None => Body::empty(),
    };
    let res = app.clone().oneshot(req.body(body).unwrap()).await.unwrap();
    let status = res.status();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let v = if bytes.is_empty() { Value::Null } else { serde_json::from_slice(&bytes).unwrap() };
    (status, v)
}

#[tokio::test]
async fn health_ok() {
    let (s, v) = call(&app(), "GET", "/health", None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(v["status"], "ok");
}

#[tokio::test]
async fn create_requires_title_and_author() {
    let (s, v) = call(&app(), "POST", "/books", Some(json!({"title": " ", "year": 2000}))).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    assert_eq!(v["details"].as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn full_crud_lifecycle() {
    let app = app();
    let (s, b) = call(&app, "POST", "/books",
        Some(json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}))).await;
    assert_eq!(s, StatusCode::CREATED);
    let id = b["id"].as_i64().unwrap();

    let (s, g) = call(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(g["title"], "Dune");

    let (s, u) = call(&app, "PUT", &format!("/books/{id}"),
        Some(json!({"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}))).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(u["title"], "Dune Messiah");

    let (s, _) = call(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NO_CONTENT);
    let (s, _) = call(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
    let (s, _) = call(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_filters_by_author() {
    let app = app();
    for (t, a) in [("A", "X"), ("B", "Y"), ("C", "X")] {
        call(&app, "POST", "/books", Some(json!({"title": t, "author": a}))).await;
    }
    let (s, all) = call(&app, "GET", "/books", None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);
    let (_, xs) = call(&app, "GET", "/books?author=X", None).await;
    assert_eq!(xs.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn update_missing_is_404() {
    let (s, _) = call(&app(), "PUT", "/books/999", Some(json!({"title": "T", "author": "A"}))).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}
