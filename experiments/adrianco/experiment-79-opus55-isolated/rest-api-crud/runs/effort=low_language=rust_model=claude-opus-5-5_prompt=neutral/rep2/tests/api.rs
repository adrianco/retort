use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use books_api::{app, Db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(Db::in_memory().unwrap())
}

async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(v) => {
            req = req.header("content-type", "application/json");
            Body::from(v.to_string())
        }
        None => Body::empty(),
    };
    let res = app.clone().oneshot(req.body(body).unwrap()).await.unwrap();
    let status = res.status();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (status, json)
}

fn dune() -> Value {
    json!({ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" })
}

#[tokio::test]
async fn health_check() {
    let (status, body) = send(&test_app(), "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();
    let (status, created) = send(&app, "POST", "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["year"], 1965);
    let id = created["id"].as_i64().unwrap();

    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_with_only_required_fields() {
    let app = test_app();
    let body = json!({ "title": "Emma", "author": "Jane Austen" });
    let (status, created) = send(&app, "POST", "/books", Some(body)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["year"], Value::Null);
    assert_eq!(created["isbn"], Value::Null);
}

#[tokio::test]
async fn create_rejects_missing_or_blank_required_fields() {
    let app = test_app();

    let (status, body) = send(&app, "POST", "/books", Some(json!({ "year": 1999 }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        body["details"],
        json!(["title is required", "author is required"])
    );

    let blank = json!({ "title": "   ", "author": "Someone" });
    let (status, body) = send(&app, "POST", "/books", Some(blank)).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["details"], json!(["title is required"]));

    let (_, list) = send(&app, "GET", "/books", None).await;
    assert_eq!(list, json!([]));
}

#[tokio::test]
async fn create_rejects_malformed_json() {
    let app = test_app();
    let req = Request::builder()
        .method("POST")
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let body: Value = serde_json::from_slice(&bytes).unwrap();
    assert!(body["error"].is_string());
}

#[tokio::test]
async fn create_rejects_wrong_type() {
    let body = json!({ "title": "Dune", "author": "Frank Herbert", "year": "long ago" });
    let (status, body) = send(&test_app(), "POST", "/books", Some(body)).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].is_string());
}

#[tokio::test]
async fn list_and_filter_by_author() {
    let app = test_app();
    send(&app, "POST", "/books", Some(dune())).await;
    let emma = json!({ "title": "Emma", "author": "Jane Austen", "year": 1815 });
    send(&app, "POST", "/books", Some(emma)).await;
    let messiah = json!({ "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969 });
    send(&app, "POST", "/books", Some(messiah)).await;

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) = send(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let titles: Vec<_> = filtered
        .as_array()
        .unwrap()
        .iter()
        .map(|b| b["title"].as_str().unwrap())
        .collect();
    assert_eq!(titles, ["Dune", "Dune Messiah"]);

    let (_, none) = send(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(none, json!([]));
}

#[tokio::test]
async fn update_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let update = json!({ "title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966 });
    let (status, updated) = send(&app, "PUT", &uri, Some(update)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Dune (Revised)");
    assert_eq!(updated["year"], 1966);
    assert_eq!(updated["isbn"], Value::Null);

    let (_, fetched) = send(&app, "GET", &uri, None).await;
    assert_eq!(fetched, updated);

    let (status, _) = send(&app, "PUT", &uri, Some(json!({ "title": "No author" }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    let (_, unchanged) = send(&app, "GET", &uri, None).await;
    assert_eq!(unchanged, updated);
}

#[tokio::test]
async fn delete_book() {
    let app = test_app();
    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let uri = format!("/books/{}", created["id"]);

    let (status, body) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, _) = send(&app, "GET", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let (status, _) = send(&app, "DELETE", &uri, None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn missing_book_returns_404() {
    let app = test_app();
    for (method, uri, body) in [
        ("GET", "/books/999", None),
        ("PUT", "/books/999", Some(dune())),
        ("DELETE", "/books/999", None),
        ("GET", "/books/not-a-number", None),
    ] {
        let (status, body) = send(&app, method, uri, body).await;
        assert_eq!(status, StatusCode::NOT_FOUND, "{method} {uri}");
        assert_eq!(body["error"], "book not found");
    }
}
