use super::*;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use tower::ServiceExt;

fn test_app() -> Router {
    app(Connection::open_in_memory().unwrap()).unwrap()
}
async fn request(
    app: &Router,
    method: &str,
    path: &str,
    body: &str,
) -> (StatusCode, serde_json::Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    assert_eq!(response.headers()[header::CONTENT_TYPE], "application/json");
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}
const BOOK: &str =
    r#"{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}"#;

#[tokio::test]
async fn complete_crud_lifecycle() {
    let app = test_app();
    assert_eq!(
        request(&app, "GET", "/books", "").await,
        (StatusCode::OK, json!([]))
    );
    let (status, created) = request(&app, "POST", "/books", BOOK).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(
        created,
        json!({"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"})
    );
    assert_eq!(
        request(&app, "GET", "/books/1", "").await,
        (StatusCode::OK, created)
    );
    let (status, updated) = request(
        &app,
        "PUT",
        "/books/1",
        r#"{"title":" Dune Messiah ","author":" Frank Herbert "}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["author"], "Frank Herbert");
    assert_eq!(updated["year"], serde_json::Value::Null);
    assert_eq!(request(&app, "GET", "/books/1", "").await.1, updated);
    assert_eq!(
        request(&app, "DELETE", "/books/1", "").await,
        (StatusCode::OK, json!({"deleted":1}))
    );
    assert_eq!(
        request(&app, "GET", "/books/1", "").await.0,
        StatusCode::NOT_FOUND
    );
}

#[tokio::test]
async fn filters_by_exact_author() {
    let app = test_app();
    request(&app, "POST", "/books", BOOK).await;
    request(
        &app,
        "POST",
        "/books",
        r#"{"title":"Earthsea","author":"Ursula Le Guin"}"#,
    )
    .await;
    assert_eq!(
        request(&app, "GET", "/books", "")
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        2
    );
    let (status, books) = request(&app, "GET", "/books?author=Frank%20Herbert", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Dune");
    assert_eq!(
        request(&app, "GET", "/books?author=Nobody", "").await.1,
        json!([])
    );
    assert_eq!(
        request(&app, "GET", "/books?author=%27%20OR%201%3D1--", "")
            .await
            .1,
        json!([])
    );
}

#[tokio::test]
async fn rejects_invalid_inputs_without_mutating_data() {
    let app = test_app();
    request(&app, "POST", "/books", BOOK).await;
    for body in [
        r#"{"author":"A"}"#,
        r#"{"title":"T"}"#,
        r#"{"title":"  ","author":"A"}"#,
        r#"{"title":"T","author":"\t\n"}"#,
        r#"{"title":"T","author":"A","year":"bad"}"#,
        "{",
        "null",
    ] {
        for (method, path) in [("POST", "/books"), ("PUT", "/books/1")] {
            let (status, error) = request(&app, method, path, body).await;
            assert_eq!(status, StatusCode::BAD_REQUEST, "{method}: {body}");
            assert!(error["error"].is_string());
        }
    }
    assert_eq!(
        request(&app, "GET", "/books/1", "").await.1["title"],
        "Dune"
    );
    assert_eq!(
        request(&app, "GET", "/books", "")
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        1
    );
}

#[tokio::test]
async fn health_and_errors_are_json() {
    let app = test_app();
    assert_eq!(
        request(&app, "GET", "/health", "").await,
        (StatusCode::OK, json!({"status":"ok"}))
    );
    for method in ["GET", "PUT", "DELETE"] {
        assert_eq!(
            request(&app, method, "/books/999", BOOK).await.0,
            StatusCode::NOT_FOUND
        );
        assert_eq!(
            request(&app, method, "/books/invalid", BOOK).await.0,
            StatusCode::BAD_REQUEST
        );
    }
    assert_eq!(
        request(&app, "GET", "/missing", "").await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(
        request(&app, "PATCH", "/books/1", BOOK).await.0,
        StatusCode::METHOD_NOT_ALLOWED
    );
}

#[tokio::test]
async fn persists_across_database_reopening() {
    let path = std::env::temp_dir().join(format!(
        "books-test-{}-{}.db",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    {
        let app = app(Connection::open(&path).unwrap()).unwrap();
        assert_eq!(
            request(&app, "POST", "/books", BOOK).await.0,
            StatusCode::CREATED
        );
    }
    {
        let app = app(Connection::open(&path).unwrap()).unwrap();
        assert_eq!(
            request(&app, "GET", "/books/1", "").await.1["title"],
            "Dune"
        );
    }
    std::fs::remove_file(path).unwrap();
}
