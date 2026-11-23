use super::*;
use axum::{
    body::{to_bytes, Body},
    http::Request,
};
use serde_json::Value;
use tower::ServiceExt;

fn setup() -> Router {
    app(Connection::open_in_memory().unwrap()).unwrap()
}
async fn call(app: &Router, method: &str, path: &str, body: Value, expected: u16) -> Value {
    let req = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap();
    let res = app.clone().oneshot(req).await.unwrap();
    assert_eq!(res.status().as_u16(), expected);
    let bytes = to_bytes(res.into_body(), usize::MAX).await.unwrap();
    if expected == 204 {
        assert!(bytes.is_empty());
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    }
}
#[tokio::test]
async fn lifecycle() {
    let app = setup();
    let mut book = call(
        &app,
        "POST",
        "/books",
        json!({"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"001"}),
        201,
    )
    .await;
    let path = format!("/books/{}", book["id"]);
    assert_eq!(book["isbn"], "001");
    assert_eq!(call(&app, "GET", &path, Value::Null, 200).await, book);
    book["title"] = json!("Dune Messiah");
    assert_eq!(call(&app, "PUT", &path, book.clone(), 200).await, book);
    assert_eq!(call(&app, "GET", &path, Value::Null, 200).await, book);
    call(&app, "DELETE", &path, Value::Null, 204).await;
    for method in ["GET", "PUT", "DELETE"] {
        call(&app, method, &path, book.clone(), 404).await;
    }
}
#[tokio::test]
async fn author_filter() {
    let app = setup();
    for author in ["A B", "C", "A B"] {
        call(
            &app,
            "POST",
            "/books",
            json!({"title":"Title","author":author}),
            201,
        )
        .await;
    }
    let all = call(&app, "GET", "/books", Value::Null, 200).await;
    assert_eq!(all.as_array().unwrap().len(), 3);
    assert_eq!(
        call(&app, "GET", "/books?author=A%20B", Value::Null, 200).await,
        json!([all[0], all[2]])
    );
}
#[tokio::test]
async fn required_fields() {
    let app = setup();
    for body in [
        json!({"author":"A"}),
        json!({"title":"T"}),
        json!({"title":" ","author":"A"}),
        json!({"title":"T","author":"\t"}),
    ] {
        call(&app, "POST", "/books", body, 422).await;
    }
    assert_eq!(
        call(&app, "GET", "/books", Value::Null, 200).await,
        json!([])
    );
}
#[tokio::test]
async fn health() {
    assert_eq!(
        call(&setup(), "GET", "/health", Value::Null, 200).await,
        json!({"status":"ok"})
    );
}
