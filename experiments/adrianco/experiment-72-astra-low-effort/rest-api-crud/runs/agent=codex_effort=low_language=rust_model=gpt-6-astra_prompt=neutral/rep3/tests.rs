use super::*;
use axum::{
    body::{to_bytes, Body},
    http::Request,
};
use serde_json::{json, Value};
use tower::ServiceExt;

async fn request(app: &Router, method: &str, uri: &str, body: &str) -> (StatusCode, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(uri)
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    assert!(response.headers()[header::CONTENT_TYPE]
        .to_str()
        .unwrap()
        .starts_with("application/json"));
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    (status, serde_json::from_slice(&body).unwrap())
}

#[tokio::test]
async fn complete_crud_lifecycle() {
    let app = app(Database::in_memory().unwrap());
    let original =
        json!({"title":" Dune ","author":" Frank Herbert ","year":1965,"isbn":"9780441172719"});
    let (status, book) = request(&app, "POST", "/books", &original.to_string()).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(book["title"], "Dune");
    assert_eq!(book["author"], "Frank Herbert");
    assert_eq!(book["year"], 1965);
    assert_eq!(book["isbn"], "9780441172719");
    let uri = format!("/books/{}", book["id"]);
    assert_eq!(request(&app, "GET", &uri, "").await, (StatusCode::OK, book));
    let (status, updated) = request(
        &app,
        "PUT",
        &uri,
        r#"{"title":"New title","author":"New author"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New title");
    assert_eq!(updated["author"], "New author");
    assert!(updated["year"].is_null());
    assert!(updated["isbn"].is_null());
    assert_eq!(request(&app, "GET", &uri, "").await.1, updated);
    assert_eq!(request(&app, "DELETE", &uri, "").await.0, StatusCode::OK);
    assert_eq!(
        request(&app, "GET", &uri, "").await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(request(&app, "GET", "/books", "").await.1, json!([]));
}

#[tokio::test]
async fn lists_and_filters_authors_exactly() {
    let app = app(Database::in_memory().unwrap());
    for author in ["A Writer", "Other", "A Writer", "O'Neil"] {
        let body = json!({"title":"Book","author":author});
        assert_eq!(
            request(&app, "POST", "/books", &body.to_string()).await.0,
            StatusCode::CREATED
        );
    }
    assert_eq!(
        request(&app, "GET", "/books", "")
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        4
    );
    let (status, books) = request(&app, "GET", "/books?author=A%20Writer", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(books.as_array().unwrap().len(), 2);
    assert!(books
        .as_array()
        .unwrap()
        .iter()
        .all(|book| book["author"] == "A Writer"));
    assert_eq!(
        request(&app, "GET", "/books?author=Nobody", "").await.1,
        json!([])
    );
    assert_eq!(
        request(&app, "GET", "/books?author=O%27Neil", "")
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        1
    );
    assert_eq!(
        request(&app, "GET", "/books?author=%27%20OR%201%3D1--", "")
            .await
            .1,
        json!([])
    );
}

#[tokio::test]
async fn invalid_input_does_not_mutate_collection() {
    let app = app(Database::in_memory().unwrap());
    request(
        &app,
        "POST",
        "/books",
        r#"{"title":"Book","author":"Author"}"#,
    )
    .await;
    for body in [
        r#"{}"#,
        r#"{"title":"Book"}"#,
        r#"{"author":"Author"}"#,
        r#"{"title":" \t ","author":"Author"}"#,
        r#"{"title":"Book","author":" "}"#,
        r#"{"title":null,"author":"Author"}"#,
        r#"{"title":"Book","author":"Author","year":"bad"}"#,
        "{",
    ] {
        for (method, uri) in [("POST", "/books"), ("PUT", "/books/1")] {
            let (status, error) = request(&app, method, uri, body).await;
            assert_eq!(status, StatusCode::BAD_REQUEST, "{method}: {body}");
            assert!(error["error"].is_string());
        }
    }
    let books = request(&app, "GET", "/books", "").await.1;
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Book");
}

#[tokio::test]
async fn missing_books_and_invalid_ids() {
    let app = app(Database::in_memory().unwrap());
    for method in ["GET", "PUT", "DELETE"] {
        let body = r#"{"title":"Book","author":"Author"}"#;
        assert_eq!(
            request(&app, method, "/books/999", body).await.0,
            StatusCode::NOT_FOUND
        );
        for id in ["abc", "0", "-1", "99999999999999999999999"] {
            assert_eq!(
                request(&app, method, &format!("/books/{id}"), body).await.0,
                StatusCode::BAD_REQUEST
            );
        }
    }
    assert_eq!(
        request(&app, "GET", "/missing", "").await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(
        request(&app, "PATCH", "/books", "").await.0,
        StatusCode::METHOD_NOT_ALLOWED
    );
}

#[tokio::test]
async fn health_and_file_persistence() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("books.sqlite");
    {
        let app = app(Database::open(&path).unwrap());
        assert_eq!(
            request(&app, "GET", "/health", "").await,
            (StatusCode::OK, json!({"status":"ok"}))
        );
        assert_eq!(
            request(
                &app,
                "POST",
                "/books",
                r#"{"title":"Persistent","author":"Writer"}"#
            )
            .await
            .0,
            StatusCode::CREATED
        );
    }
    let reopened = app(Database::open(&path).unwrap());
    assert_eq!(
        request(&reopened, "GET", "/books/1", "").await.1["title"],
        "Persistent"
    );
}
