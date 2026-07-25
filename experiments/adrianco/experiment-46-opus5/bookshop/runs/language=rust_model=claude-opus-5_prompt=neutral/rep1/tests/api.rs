//! Integration tests: drive the real router against a private in-memory
//! database, so every test starts from an empty collection and no socket is
//! needed.

use axum::Router;
use axum::body::Body;
use axum::http::{Request, StatusCode, header};
use book_api::{AppState, app};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

fn test_app() -> Router {
    app(AppState::in_memory().expect("in-memory database"))
}

/// Send one request and read back the status plus the parsed JSON body
/// (`Value::Null` for empty bodies such as 204s).
async fn send(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(value) => {
            builder = builder.header(header::CONTENT_TYPE, "application/json");
            Body::from(value.to_string())
        }
        None => Body::empty(),
    };

    let response = app
        .clone()
        .oneshot(builder.body(body).expect("valid request"))
        .await
        .expect("router should not fail");

    let status = response.status();
    let bytes = response
        .into_body()
        .collect()
        .await
        .expect("body should be readable")
        .to_bytes();

    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("response body should be JSON")
    };
    (status, json)
}

/// Raw variant for bodies that are not valid JSON.
async fn send_raw(app: &Router, uri: &str, raw: &'static str) -> (StatusCode, Value) {
    let request = Request::builder()
        .method("POST")
        .uri(uri)
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from(raw))
        .expect("valid request");

    let response = app.clone().oneshot(request).await.expect("router");
    let status = response.status();
    let bytes = response
        .into_body()
        .collect()
        .await
        .expect("body")
        .to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).expect("JSON error body"),
    )
}

fn dune() -> Value {
    json!({
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0-441-01359-3"
    })
}

#[tokio::test]
async fn health_reports_ok_and_reaches_the_database() {
    let app = test_app();

    let (status, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({"status": "ok", "books": 0}));

    send(&app, "POST", "/books", Some(dune())).await;

    let (_, body) = send(&app, "GET", "/health", None).await;
    assert_eq!(body["books"], 1);
}

#[tokio::test]
async fn create_then_read_back_a_book() {
    let app = test_app();

    let (status, created) = send(&app, "POST", "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    assert_eq!(created["isbn"], "978-0-441-01359-3");

    let id = created["id"].as_i64().expect("id should be a number");
    let (status, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn optional_fields_may_be_omitted() {
    let app = test_app();

    let (status, created) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "Untitled Draft", "author": "Anon"})),
    )
    .await;

    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["year"], Value::Null);
    assert_eq!(created["isbn"], Value::Null);
}

#[tokio::test]
async fn create_rejects_missing_title_and_author() {
    let app = test_app();

    let (status, body) = send(&app, "POST", "/books", Some(json!({"year": 1965}))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["error"], "validation failed");

    let details: Vec<&str> = body["details"]
        .as_array()
        .expect("details array")
        .iter()
        .map(|d| d.as_str().expect("detail string"))
        .collect();
    assert_eq!(details, vec!["title is required", "author is required"]);

    // Nothing was persisted.
    let (_, books) = send(&app, "GET", "/books", None).await;
    assert_eq!(books.as_array().expect("array").len(), 0);
}

#[tokio::test]
async fn create_rejects_blank_title() {
    let app = test_app();

    let (status, body) = send(
        &app,
        "POST",
        "/books",
        Some(json!({"title": "   ", "author": "Frank Herbert"})),
    )
    .await;

    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["details"], json!(["title must not be empty"]));
}

#[tokio::test]
async fn malformed_json_returns_a_json_error() {
    let app = test_app();

    let (status, body) = send_raw(&app, "/books", "{not json").await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(
        body["error"]
            .as_str()
            .expect("error string")
            .contains("JSON"),
        "unexpected body: {body}"
    );
}

#[tokio::test]
async fn list_returns_newest_first_and_filters_by_author() {
    let app = test_app();

    for book in [
        json!({"title": "Dune", "author": "Frank Herbert", "year": 1965}),
        json!({"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}),
        json!({"title": "Neuromancer", "author": "William Gibson", "year": 1984}),
    ] {
        let (status, _) = send(&app, "POST", "/books", Some(book)).await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = send(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    let titles: Vec<&str> = all
        .as_array()
        .expect("array")
        .iter()
        .map(|b| b["title"].as_str().expect("title"))
        .collect();
    assert_eq!(titles, vec!["Neuromancer", "Dune Messiah", "Dune"]);

    // The filter is case-insensitive and URL-encoded spaces work.
    let (status, filtered) = send(&app, "GET", "/books?author=frank%20herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let titles: Vec<&str> = filtered
        .as_array()
        .expect("array")
        .iter()
        .map(|b| b["title"].as_str().expect("title"))
        .collect();
    assert_eq!(titles, vec!["Dune Messiah", "Dune"]);

    let (status, none) = send(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(none, json!([]));
}

#[tokio::test]
async fn update_replaces_every_field() {
    let app = test_app();

    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let id = created["id"].as_i64().expect("id");

    let (status, updated) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "Dune (Revised)", "author": "F. Herbert"})),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        updated,
        json!({
            "id": id,
            "title": "Dune (Revised)",
            "author": "F. Herbert",
            "year": null,
            "isbn": null
        })
    );

    let (_, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(fetched, updated);
}

#[tokio::test]
async fn update_validates_its_body() {
    let app = test_app();

    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let id = created["id"].as_i64().expect("id");

    let (status, body) = send(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({"title": "Dune"})),
    )
    .await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(body["details"], json!(["author is required"]));

    // The stored book is untouched.
    let (_, fetched) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn delete_removes_the_book() {
    let app = test_app();

    let (_, created) = send(&app, "POST", "/books", Some(dune())).await;
    let id = created["id"].as_i64().expect("id");

    let (status, body) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert_eq!(body, Value::Null);

    let (status, _) = send(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Deleting again is a 404, not a silent success.
    let (status, _) = send(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn unknown_ids_and_routes_return_json_404s() {
    let app = test_app();

    for (method, uri) in [("GET", "/books/999"), ("DELETE", "/books/999")] {
        let (status, body) = send(&app, method, uri, None).await;
        assert_eq!(status, StatusCode::NOT_FOUND, "{method} {uri}");
        assert_eq!(body["error"], "book 999 not found");
    }

    let (status, body) = send(
        &app,
        "PUT",
        "/books/999",
        Some(json!({"title": "Ghost", "author": "Nobody"})),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book 999 not found");

    let (status, body) = send(&app, "GET", "/nope", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "no such route");
}

#[tokio::test]
async fn non_numeric_ids_are_rejected() {
    let app = test_app();

    let (status, body) = send(&app, "GET", "/books/abc", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "invalid book id: \"abc\"");
}

#[tokio::test]
async fn books_persist_across_requests_in_the_same_database() {
    let state = AppState::in_memory().expect("in-memory database");

    let (status, created) = send(&app(state.clone()), "POST", "/books", Some(dune())).await;
    assert_eq!(status, StatusCode::CREATED);

    // A freshly built router over the same state still sees the book.
    let (status, fetched) = send(
        &app(state),
        "GET",
        &format!("/books/{}", created["id"]),
        None,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}
