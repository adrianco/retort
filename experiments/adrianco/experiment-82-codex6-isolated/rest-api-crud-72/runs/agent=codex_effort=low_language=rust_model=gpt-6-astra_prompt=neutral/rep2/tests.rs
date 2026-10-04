use super::*;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn test_app() -> Router {
    app(Connection::open_in_memory().unwrap()).unwrap()
}
async fn request(
    app: &Router,
    method: &str,
    path: &str,
    body: Option<Value>,
) -> (StatusCode, Value) {
    let mut request = Request::builder().method(method).uri(path);
    if body.is_some() {
        request = request.header("content-type", "application/json");
    }
    let response = app
        .clone()
        .oneshot(
            request
                .body(
                    body.map(|v| Body::from(v.to_string()))
                        .unwrap_or_else(Body::empty),
                )
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    if status != StatusCode::NO_CONTENT {
        assert_eq!(response.headers()[header::CONTENT_TYPE], "application/json");
    }
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
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
    let input =
        json!({"title":" Dune ","author":" Frank Herbert ","year":1965,"isbn":"9780441172719"});
    let (status, created) = request(&app, "POST", "/books", Some(input)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Frank Herbert");
    assert_eq!(created["year"], 1965);
    assert_eq!(created["isbn"], "9780441172719");
    let path = format!("/books/{}", created["id"]);
    assert_eq!(
        request(&app, "GET", &path, None).await,
        (StatusCode::OK, created)
    );
    let (status, updated) = request(
        &app,
        "PUT",
        &path,
        Some(json!({"title":"Dune Messiah","author":"Frank Herbert"})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Dune Messiah");
    assert!(updated["year"].is_null());
    assert!(updated["isbn"].is_null());
    assert_eq!(request(&app, "GET", &path, None).await.1, updated);
    assert_eq!(
        request(&app, "DELETE", &path, None).await,
        (StatusCode::NO_CONTENT, Value::Null)
    );
    assert_eq!(
        request(&app, "GET", &path, None).await.0,
        StatusCode::NOT_FOUND
    );
    assert_eq!(request(&app, "GET", "/books", None).await.1, json!([]));
}

#[tokio::test]
async fn list_and_filter_by_exact_author() {
    let app = test_app();
    for (title, author) in [("A", "Some Author"), ("B", "Other"), ("C", "Some Author")] {
        assert_eq!(
            request(
                &app,
                "POST",
                "/books",
                Some(json!({"title":title,"author":author}))
            )
            .await
            .0,
            StatusCode::CREATED
        );
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
    let (status, filtered) = request(&app, "GET", "/books?author=Some%20Author", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(filtered.as_array().unwrap().len(), 2);
    assert_eq!(filtered[0]["title"], "A");
    assert_eq!(filtered[1]["title"], "C");
    assert_eq!(
        request(&app, "GET", "/books?author=%27%20OR%201%3D1--", None)
            .await
            .1,
        json!([])
    );
}

#[tokio::test]
async fn validation_rejects_invalid_create_and_update_without_mutation() {
    let app = test_app();
    request(
        &app,
        "POST",
        "/books",
        Some(json!({"title":"Original","author":"Author"})),
    )
    .await;
    for input in [
        json!({}),
        json!({"title":"T"}),
        json!({"author":"A"}),
        json!({"title":" \n","author":"A"}),
        json!({"title":"T","author":"\t"}),
        json!({"title":null,"author":"A"}),
        json!({"title":"T","author":"A","year":"bad"}),
    ] {
        for (method, path) in [("POST", "/books"), ("PUT", "/books/1")] {
            let (status, body) = request(&app, method, path, Some(input.clone())).await;
            assert_eq!(status, StatusCode::BAD_REQUEST);
            assert!(body["error"].is_string());
        }
    }
    let (_, books) = request(&app, "GET", "/books", None).await;
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Original");
}

#[tokio::test]
async fn health_missing_books_and_invalid_ids() {
    let app = test_app();
    assert_eq!(
        request(&app, "GET", "/health", None).await,
        (StatusCode::OK, json!({"status":"ok"}))
    );
    for method in ["GET", "PUT", "DELETE"] {
        let body = if method == "PUT" {
            Some(json!({"title":"T","author":"A"}))
        } else {
            None
        };
        assert_eq!(
            request(&app, method, "/books/999", body.clone()).await.0,
            StatusCode::NOT_FOUND
        );
        for id in ["abc", "0", "-1", "999999999999999999999999"] {
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
        request(&app, "PATCH", "/books", None).await.0,
        StatusCode::METHOD_NOT_ALLOWED
    );
}

#[tokio::test]
async fn malformed_json_and_missing_content_type_return_json_errors() {
    let app = test_app();
    for (content_type, body, expected) in [
        (Some("application/json"), "{", StatusCode::BAD_REQUEST),
        (None, "{}", StatusCode::UNSUPPORTED_MEDIA_TYPE),
    ] {
        let mut req = Request::builder().method("POST").uri("/books");
        if let Some(value) = content_type {
            req = req.header(header::CONTENT_TYPE, value);
        }
        let response = app
            .clone()
            .oneshot(req.body(Body::from(body)).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), expected);
        let bytes = response.into_body().collect().await.unwrap().to_bytes();
        assert!(serde_json::from_slice::<Value>(&bytes).unwrap()["error"].is_string());
    }
}

#[tokio::test]
async fn sqlite_data_survives_reopening() {
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
            request(
                &app,
                "POST",
                "/books",
                Some(json!({"title":"Persistent","author":"Author"}))
            )
            .await
            .0,
            StatusCode::CREATED
        );
    }
    {
        let app = app(Connection::open(&path).unwrap()).unwrap();
        assert_eq!(
            request(&app, "GET", "/books/1", None).await.1["title"],
            "Persistent"
        );
    }
    std::fs::remove_file(path).unwrap();
}
