use super::*;
use axum::{
    body::{to_bytes, Body},
    http::Request,
};
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(Database::open(":memory:").unwrap())
}
async fn request(
    app: &Router,
    method: &str,
    uri: &str,
    body: Option<Value>,
) -> (StatusCode, Value) {
    let body = body.map(|v| v.to_string()).unwrap_or_default();
    raw_request(app, method, uri, &body).await
}
async fn raw_request(app: &Router, method: &str, uri: &str, body: &str) -> (StatusCode, Value) {
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
    if status != StatusCode::NO_CONTENT {
        assert_eq!(response.headers()["content-type"], "application/json");
    }
    let bytes = to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    (
        status,
        if bytes.is_empty() {
            Value::Null
        } else {
            serde_json::from_slice(&bytes).unwrap()
        },
    )
}

#[tokio::test]
async fn crud_lifecycle() {
    let app = test_app();
    let (status, book) = request(
        &app,
        "POST",
        "/books",
        Some(json!({"title":" Dune ","author":"Frank Herbert","year":1965,"isbn":"9780441172719"})),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(book["title"], "Dune");
    assert_eq!(book["year"], 1965);
    assert_eq!(book["isbn"], "9780441172719");
    let uri = format!("/books/{}", book["id"]);
    assert_eq!(
        request(&app, "GET", &uri, None).await,
        (StatusCode::OK, book)
    );
    let (status, updated) = request(
        &app,
        "PUT",
        &uri,
        Some(json!({"title":"Dune Messiah","author":"Frank Herbert"})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["year"], Value::Null);
    assert_eq!(request(&app, "GET", &uri, None).await.1, updated);
    assert_eq!(
        request(&app, "DELETE", &uri, None).await,
        (StatusCode::NO_CONTENT, Value::Null)
    );
    assert_eq!(
        request(&app, "GET", &uri, None).await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(request(&app, "GET", "/books", None).await.1, json!([]));
}

#[tokio::test]
async fn lists_and_filters_authors_exactly() {
    let app = test_app();
    for author in ["Ursula Le Guin", "Other", "Ursula Le Guin"] {
        request(
            &app,
            "POST",
            "/books",
            Some(json!({"title":"Book", "author":author})),
        )
        .await;
    }
    assert_eq!(
        request(&app, "GET", "/books", None)
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        3
    );
    let (status, books) = request(&app, "GET", "/books?author=Ursula%20Le%20Guin", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(books.as_array().unwrap().len(), 2);
    assert!(books
        .as_array()
        .unwrap()
        .iter()
        .all(|b| b["author"] == "Ursula Le Guin"));
    assert_eq!(
        request(&app, "GET", "/books?author=Nobody", None).await.1,
        json!([])
    );
    assert_eq!(
        request(&app, "GET", "/books?author=%27%20OR%201%3D1--", None)
            .await
            .1,
        json!([])
    );
}

#[tokio::test]
async fn rejects_invalid_input_without_mutation() {
    let app = test_app();
    request(
        &app,
        "POST",
        "/books",
        Some(json!({"title":"Original","author":"Author"})),
    )
    .await;
    for payload in [
        json!({}),
        json!({"title":"Book"}),
        json!({"author":"Author"}),
        json!({"title":" \n ","author":"Author"}),
        json!({"title":"Book","author":"\t"}),
        json!({"title":"Book","author":"Author","year":"yesterday"}),
    ] {
        for (method, uri) in [("POST", "/books"), ("PUT", "/books/1")] {
            let (status, error) = request(&app, method, uri, Some(payload.clone())).await;
            assert_eq!(status, StatusCode::BAD_REQUEST);
            assert!(error["error"].is_string());
        }
    }
    assert_eq!(
        raw_request(&app, "POST", "/books", "{invalid").await.0,
        StatusCode::BAD_REQUEST
    );
    let books = request(&app, "GET", "/books", None).await.1;
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Original");
}

#[tokio::test]
async fn missing_books_invalid_ids_and_health() {
    let app = test_app();
    assert_eq!(
        request(&app, "GET", "/health", None).await,
        (StatusCode::OK, json!({"status":"ok"}))
    );
    for method in ["GET", "PUT", "DELETE"] {
        let body = Some(json!({"title":"Title", "author":"Author"}));
        assert_eq!(
            request(&app, method, "/books/999", body.clone()).await.0,
            StatusCode::NOT_FOUND
        );
        for id in ["abc", "0", "-1", "9999999999999999999999999"] {
            assert_eq!(
                request(&app, method, &format!("/books/{id}"), body.clone())
                    .await
                    .0,
                StatusCode::BAD_REQUEST
            );
        }
    }
    assert_eq!(
        request(&app, "GET", "/unknown", None).await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(
        request(&app, "PATCH", "/books/1", None).await.0,
        StatusCode::METHOD_NOT_ALLOWED
    );
}

#[tokio::test]
async fn data_survives_database_reopening() {
    let path = std::env::temp_dir().join(format!(
        "book-api-{}-{}.db",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let filename = path.to_str().unwrap();
    {
        let app = app(Database::open(filename).unwrap());
        assert_eq!(
            request(
                &app,
                "POST",
                "/books",
                Some(json!({"title":"Persistent", "author":"Author"}))
            )
            .await
            .0,
            StatusCode::CREATED
        );
    }
    {
        let app = app(Database::open(filename).unwrap());
        let (status, book) = request(&app, "GET", "/books/1", None).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(book["title"], "Persistent");
    }
    std::fs::remove_file(path).unwrap();
}
