//! Integration tests for the book collection REST API, written in BDD style:
//! each test documents its own Given / When / Then in comments and asserts
//! a single observable behaviour.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use book_api::{app, db};

/// Builds a fresh router backed by its own isolated in-memory database, so
/// tests never see each other's data.
fn test_app() -> axum::Router {
    let pool = db::init_pool(":memory:");
    app(pool)
}

async fn body_json(response: axum::response::Response) -> Value {
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

fn json_request(method: &str, uri: &str, body: Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_vec(&body).unwrap()))
        .unwrap()
}

fn get_request(uri: &str) -> Request<Body> {
    Request::builder()
        .method("GET")
        .uri(uri)
        .body(Body::empty())
        .unwrap()
}

#[tokio::test]
async fn test_given_running_service_when_health_checked_then_status_is_ok() {
    // Given a running service
    let app = test_app();

    // When the health endpoint is checked
    let response = app.oneshot(get_request("/health")).await.unwrap();

    // Then it reports healthy with a 200 status
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn test_given_valid_book_data_when_creating_book_then_response_is_created_with_id() {
    // Given valid book data
    let app = test_app();
    let payload = json!({
        "title": "The Pragmatic Programmer",
        "author": "David Thomas",
        "year": 1999,
        "isbn": "978-0135957059"
    });

    // When a book is created
    let response = app
        .oneshot(json_request("POST", "/books", payload))
        .await
        .unwrap();

    // Then the response is 201 Created and includes a generated id
    assert_eq!(response.status(), StatusCode::CREATED);
    let body = body_json(response).await;
    assert!(body["id"].is_i64());
    assert_eq!(body["title"], "The Pragmatic Programmer");
}

#[tokio::test]
async fn test_given_missing_title_when_creating_book_then_response_is_bad_request() {
    // Given book data missing the required title field
    let app = test_app();
    let payload = json!({
        "title": "",
        "author": "David Thomas"
    });

    // When a book is created
    let response = app
        .oneshot(json_request("POST", "/books", payload))
        .await
        .unwrap();

    // Then the request is rejected as a validation error
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_given_missing_author_when_creating_book_then_response_is_bad_request() {
    // Given book data missing the required author field
    let app = test_app();
    let payload = json!({
        "title": "Some Title",
        "author": ""
    });

    // When a book is created
    let response = app
        .oneshot(json_request("POST", "/books", payload))
        .await
        .unwrap();

    // Then the request is rejected as a validation error
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_given_existing_book_when_fetched_by_id_then_returns_matching_book() {
    // Given a book that already exists in the collection
    let app = test_app();
    let create_payload = json!({ "title": "Dune", "author": "Frank Herbert" });
    let create_response = app
        .clone()
        .oneshot(json_request("POST", "/books", create_payload))
        .await
        .unwrap();
    let created = body_json(create_response).await;
    let id = created["id"].as_i64().unwrap();

    // When that book is fetched by its id
    let response = app
        .oneshot(get_request(&format!("/books/{id}")))
        .await
        .unwrap();

    // Then the matching book is returned
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["title"], "Dune");
    assert_eq!(body["author"], "Frank Herbert");
}

#[tokio::test]
async fn test_given_no_book_with_id_when_fetched_then_response_is_not_found() {
    // Given a collection with no book at id 999
    let app = test_app();

    // When that id is fetched
    let response = app.oneshot(get_request("/books/999")).await.unwrap();

    // Then a 404 is returned
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_given_books_by_different_authors_when_listed_with_author_filter_then_only_matches_returned(
) {
    // Given books written by different authors
    let app = test_app();
    app.clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Dune", "author": "Frank Herbert" }),
        ))
        .await
        .unwrap();
    app.clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Children of Dune", "author": "Frank Herbert" }),
        ))
        .await
        .unwrap();
    app.clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Foundation", "author": "Isaac Asimov" }),
        ))
        .await
        .unwrap();

    // When the list is filtered by author
    let response = app
        .oneshot(get_request("/books?author=Frank%20Herbert"))
        .await
        .unwrap();

    // Then only that author's books are returned
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Frank Herbert"));
}

#[tokio::test]
async fn test_given_existing_book_when_updated_then_response_reflects_new_values() {
    // Given a book that already exists
    let app = test_app();
    let create_response = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Old Title", "author": "Old Author" }),
        ))
        .await
        .unwrap();
    let created = body_json(create_response).await;
    let id = created["id"].as_i64().unwrap();

    // When it is updated with new details
    let update_payload = json!({
        "title": "New Title",
        "author": "New Author",
        "year": 2020,
        "isbn": "111-1"
    });
    let response = app
        .oneshot(json_request(
            "PUT",
            &format!("/books/{id}"),
            update_payload,
        ))
        .await
        .unwrap();

    // Then the response reflects the updated values
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["title"], "New Title");
    assert_eq!(body["author"], "New Author");
    assert_eq!(body["year"], 2020);
}

#[tokio::test]
async fn test_given_no_book_with_id_when_updated_then_response_is_not_found() {
    // Given a collection with no book at id 999
    let app = test_app();

    // When an update is attempted against that id
    let response = app
        .oneshot(json_request(
            "PUT",
            "/books/999",
            json!({ "title": "X", "author": "Y" }),
        ))
        .await
        .unwrap();

    // Then a 404 is returned
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_given_existing_book_when_deleted_then_it_is_no_longer_retrievable() {
    // Given a book that already exists
    let app = test_app();
    let create_response = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Ephemeral", "author": "Nobody" }),
        ))
        .await
        .unwrap();
    let created = body_json(create_response).await;
    let id = created["id"].as_i64().unwrap();

    // When it is deleted
    let delete_response = app
        .clone()
        .oneshot(Request::builder()
            .method("DELETE")
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap())
        .await
        .unwrap();
    assert_eq!(delete_response.status(), StatusCode::NO_CONTENT);

    // Then it can no longer be retrieved
    let get_response = app
        .oneshot(get_request(&format!("/books/{id}")))
        .await
        .unwrap();
    assert_eq!(get_response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_given_no_book_with_id_when_deleted_then_response_is_not_found() {
    // Given a collection with no book at id 999
    let app = test_app();

    // When a delete is attempted against that id
    let response = app
        .oneshot(Request::builder()
            .method("DELETE")
            .uri("/books/999")
            .body(Body::empty())
            .unwrap())
        .await
        .unwrap();

    // Then a 404 is returned
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
