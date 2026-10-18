use axum::{
    body::Body,
    http::{Method, Request, StatusCode},
    Router,
};
use book_api::{app, AppState};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn router() -> Router {
    app(AppState::in_memory().expect("in-memory db"))
}

async fn send(router: &Router, method: Method, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(json) => {
            builder = builder.header("content-type", "application/json");
            Body::from(json.to_string())
        }
        None => Body::empty(),
    };
    let response = router
        .clone()
        .oneshot(builder.body(body).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap_or(Value::Null)
    };
    (status, json)
}

fn dune() -> Value {
    json!({ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" })
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = router();
    let (status, body) = send(&app, Method::GET, "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn full_crud_lifecycle() {
    let app = router();

    // Create
    let (status, created) = send(&app, Method::POST, "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);
    let id = created["id"].as_i64().unwrap();
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["year"], 1965);

    // Get
    let (status, fetched) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);

    // Update
    let update = json!({ "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969 });
    let (status, updated) = send(&app, Method::PUT, &format!("/books/{id}"), Some(update)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["id"], id);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["isbn"], Value::Null);

    // Delete
    let (status, _) = send(&app, Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    let (status, _) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_filters_by_author_case_insensitively() {
    let app = router();
    send(&app, Method::POST, "/books", Some(dune())).await;
    send(
        &app,
        Method::POST,
        "/books",
        Some(json!({ "title": "Emma", "author": "Jane Austen" })),
    )
    .await;

    let (status, all) = send(&app, Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 2);

    let (status, filtered) = send(&app, Method::GET, "/books?author=frank%20herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 1);
    assert_eq!(filtered[0]["title"], "Dune");
}

#[tokio::test]
async fn create_rejects_missing_or_blank_required_fields() {
    let app = router();

    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "author": "A" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) =
        send(&app, Method::POST, "/books", Some(json!({ "title": "   ", "author": "A" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    let (status, body) = send(&app, Method::POST, "/books", Some(json!({ "title": "T" }))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author is required");
}

#[tokio::test]
async fn invalid_year_and_isbn_are_rejected() {
    let app = router();

    let bad_year = json!({ "title": "T", "author": "A", "year": -5 });
    let (status, _) = send(&app, Method::POST, "/books", Some(bad_year)).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let bad_isbn = json!({ "title": "T", "author": "A", "isbn": "abc" });
    let (status, _) = send(&app, Method::POST, "/books", Some(bad_isbn)).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn malformed_json_is_a_bad_request() {
    let app = router();
    let request = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from("{not json"))
        .unwrap();
    let response = app.clone().oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn unknown_book_returns_404_for_get_put_and_delete() {
    let app = router();
    let valid = json!({ "title": "T", "author": "A" });

    let (status, body) = send(&app, Method::GET, "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book not found");

    let (status, _) = send(&app, Method::PUT, "/books/999", Some(valid)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(&app, Method::DELETE, "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn update_with_invalid_body_is_rejected() {
    let app = router();
    let (_, created) = send(&app, Method::POST, "/books", Some(dune())).await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = send(
        &app,
        Method::PUT,
        &format!("/books/{id}"),
        Some(json!({ "title": "", "author": "A" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // The original record must be untouched.
    let (_, fetched) = send(&app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(fetched["title"], "Dune");
}
