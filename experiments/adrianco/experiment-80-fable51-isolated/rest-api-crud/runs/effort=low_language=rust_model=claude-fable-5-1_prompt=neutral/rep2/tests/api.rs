use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use books_api::{app, open_db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(open_db(":memory:").unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let builder = Request::builder().method(method).uri(uri);
    let req = match body {
        Some(b) => builder
            .header("content-type", "application/json")
            .body(Body::from(b.to_string()))
            .unwrap(),
        None => builder.body(Body::empty()).unwrap(),
    };
    let resp = app.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, value)
}

#[tokio::test]
async fn health_check() {
    let app = test_app();
    let (status, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({"status": "ok"}));
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let input = json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"});
    let (status, created) = send(&app, "POST", "/books", Some(input)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn validation_rejects_missing_title_and_author() {
    let app = test_app();
    let (status, body) = send(&app, "POST", "/books", Some(json!({"year": 2000}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["details"].as_array().unwrap().len(), 2);

    let (status, _) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "  ", "author": "Someone"})),
    )
    .await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    let (_, list) = send(&app, "GET", "/books", None).await;
    assert_eq!(list, json!([]));
}

#[tokio::test]
async fn malformed_json_is_bad_request() {
    let app = test_app();
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let resp = app.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_with_author_filter() {
    let app = test_app();
    for (t, a) in [("Dune", "Frank Herbert"), ("Emma", "Jane Austen"), ("Persuasion", "Jane Austen")] {
        send(&app, "POST", "/books", Some(json!({"title": t, "author": a}))).await;
    }
    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (_, austen) = send(&app, "GET", "/books?author=Jane%20Austen", None).await;
    let austen = austen.as_array().unwrap();
    assert_eq!(austen.len(), 2);
    assert!(austen.iter().all(|b| b["author"] == "Jane Austen"));

    let (_, none) = send(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(none, json!([]));
}

#[tokio::test]
async fn update_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(json!({"title": "Old", "author": "A"}))).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, updated) = send(
        &app,
        "PUT",
        &uri,
        Some(json!({"title": "New", "author": "B", "year": 2020})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["year"], 2020);

    let (_, fetched) = send(&app, "GET", &uri, None).await;
    assert_eq!(fetched, updated);

    let (status, _) = send(&app, "PUT", &uri, Some(json!({"title": "", "author": "B"}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    let (status, _) = send(&app, "PUT", "/books/999", Some(json!({"title": "X", "author": "Y"}))).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(json!({"title": "T", "author": "A"}))).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, _) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    let (status, body) = send(&app, "GET", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");
    let (status, _) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}
