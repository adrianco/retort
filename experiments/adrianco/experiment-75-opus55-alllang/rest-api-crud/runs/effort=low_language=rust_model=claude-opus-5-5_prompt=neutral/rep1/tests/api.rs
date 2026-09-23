use axum::{body::Body, http::{Request, StatusCode}, Router};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn app() -> Router { books_api::app(books_api::open_db(":memory:").unwrap()) }

async fn call(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(b) => { req = req.header("content-type", "application/json"); Body::from(b.to_string()) }
        None => Body::empty(),
    };
    let res = app.clone().oneshot(req.body(body).unwrap()).await.unwrap();
    let status = res.status();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

#[tokio::test]
async fn health_ok() {
    let (s, b) = call(&app(), "GET", "/health", None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(b["status"], "ok");
}

#[tokio::test]
async fn crud_lifecycle() {
    let app = app();
    let (s, b) = call(&app, "POST", "/books", Some(json!({"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}))).await;
    assert_eq!(s, StatusCode::CREATED);
    let id = b["id"].as_i64().unwrap();
    let (s, b) = call(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(b["title"], "Dune");
    let (s, b) = call(&app, "PUT", &format!("/books/{id}"), Some(json!({"title":"Dune Messiah","author":"Herbert","year":1969}))).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(b["year"], 1969);
    let (s, _) = call(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NO_CONTENT);
    let (s, _) = call(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
    let (s, _) = call(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_requires_title_and_author() {
    let app = app();
    let (s, b) = call(&app, "POST", "/books", Some(json!({"title":"  "}))).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    assert!(b["error"].as_str().unwrap().contains("title"));
    assert!(b["error"].as_str().unwrap().contains("author"));
    let (_, b) = call(&app, "POST", "/books", Some(json!({"title":"A","author":"B"}))).await;
    let (s, _) = call(&app, "PUT", &format!("/books/{}", b["id"]), Some(json!({"title":"A"}))).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    let (s, _) = call(&app, "PUT", "/books/999", Some(json!({"title":"A","author":"B"}))).await;
    assert_eq!(s, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_with_author_filter() {
    let app = app();
    for (t, a) in [("A", "X"), ("B", "Y"), ("C", "X")] {
        call(&app, "POST", "/books", Some(json!({"title":t,"author":a}))).await;
    }
    let (s, b) = call(&app, "GET", "/books", None).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(b.as_array().unwrap().len(), 3);
    let (_, b) = call(&app, "GET", "/books?author=X", None).await;
    let titles: Vec<_> = b.as_array().unwrap().iter().map(|x| x["title"].as_str().unwrap()).collect();
    assert_eq!(titles, ["A", "C"]);
}
