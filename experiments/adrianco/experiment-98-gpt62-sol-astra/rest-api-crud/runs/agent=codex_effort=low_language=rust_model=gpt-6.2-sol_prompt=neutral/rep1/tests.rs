use super::*;
use axum::{
    body::{Body, to_bytes},
    http::{Method, Request},
};
use serde_json::Value;
use tower::ServiceExt;

async fn test_app() -> Router {
    let db = open_database(SqliteConnectOptions::new().in_memory(true))
        .await
        .unwrap();
    app(db)
}

async fn request(
    app: &Router,
    method: Method,
    uri: &str,
    body: Option<Value>,
    expected: StatusCode,
) -> Value {
    let mut request = Request::builder().method(method).uri(uri);
    let body = match body {
        Some(value) => {
            request = request.header(header::CONTENT_TYPE, "application/json");
            Body::from(value.to_string())
        }
        None => Body::empty(),
    };
    let response = app
        .clone()
        .oneshot(request.body(body).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), expected);
    if expected == StatusCode::CREATED {
        assert!(
            response.headers()[header::LOCATION]
                .to_str()
                .unwrap()
                .starts_with("/books/")
        );
    }
    if expected != StatusCode::NO_CONTENT {
        assert_eq!(response.headers()[header::CONTENT_TYPE], "application/json");
    }
    let bytes = to_bytes(response.into_body(), 64 * 1024).await.unwrap();
    if expected == StatusCode::NO_CONTENT {
        assert!(bytes.is_empty());
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    }
}

#[tokio::test]
async fn book_lifecycle() {
    let app = test_app().await;
    let input = json!({
        "title": "Kindred", "author": "Octavia Butler", "year": 1979, "isbn": "9780807083697"
    });
    let created = request(
        &app,
        Method::POST,
        "/books",
        Some(input.clone()),
        StatusCode::CREATED,
    )
    .await;
    let id = created["id"].as_i64().unwrap();
    let mut expected = input;
    expected["id"] = json!(id);
    assert_eq!(created, expected);
    let uri = format!("/books/{id}");
    assert_eq!(
        request(&app, Method::GET, &uri, None, StatusCode::OK).await,
        created
    );

    let updated = request(
        &app,
        Method::PUT,
        &uri,
        Some(json!({"title": "Parable of the Sower", "author": "Octavia Butler", "year": 1993})),
        StatusCode::OK,
    )
    .await;
    assert_eq!(
        updated,
        json!({
            "id": id, "title": "Parable of the Sower", "author": "Octavia Butler", "year": 1993, "isbn": null
        })
    );
    assert_eq!(
        request(&app, Method::GET, &uri, None, StatusCode::OK).await,
        updated
    );
    request(&app, Method::DELETE, &uri, None, StatusCode::NO_CONTENT).await;
    request(&app, Method::GET, &uri, None, StatusCode::NOT_FOUND).await;
    request(&app, Method::DELETE, &uri, None, StatusCode::NOT_FOUND).await;
    request(
        &app,
        Method::PUT,
        &uri,
        Some(updated),
        StatusCode::NOT_FOUND,
    )
    .await;
}

#[tokio::test]
async fn list_filters_by_author() {
    let app = test_app().await;
    assert_eq!(
        request(&app, Method::GET, "/books", None, StatusCode::OK).await,
        json!([])
    );
    let first = request(
        &app,
        Method::POST,
        "/books",
        Some(json!({"title": "Kindred", "author": "Octavia Butler"})),
        StatusCode::CREATED,
    )
    .await;
    let second = request(
        &app,
        Method::POST,
        "/books",
        Some(json!({"title": "Beloved", "author": "Toni Morrison"})),
        StatusCode::CREATED,
    )
    .await;
    assert_eq!(
        request(&app, Method::GET, "/books", None, StatusCode::OK).await,
        json!([first, second])
    );
    assert_eq!(
        request(
            &app,
            Method::GET,
            "/books?author=Octavia%20Butler",
            None,
            StatusCode::OK
        )
        .await,
        json!([first])
    );
    assert_eq!(
        request(
            &app,
            Method::GET,
            "/books?author=Octavia",
            None,
            StatusCode::OK
        )
        .await,
        json!([])
    );
}

#[tokio::test]
async fn validates_required_fields_and_ids() {
    let app = test_app().await;
    for invalid_book in [
        json!({"author": "Octavia Butler"}),
        json!({"title": "Kindred"}),
        json!({"title": " ", "author": "Octavia Butler"}),
        json!({"title": "Kindred", "author": "\t"}),
    ] {
        for (method, uri) in [(Method::POST, "/books"), (Method::PUT, "/books/1")] {
            let error = request(
                &app,
                method,
                uri,
                Some(invalid_book.clone()),
                StatusCode::UNPROCESSABLE_ENTITY,
            )
            .await;
            assert!(error["error"].is_string());
        }
    }
    request(
        &app,
        Method::GET,
        "/books/abc",
        None,
        StatusCode::BAD_REQUEST,
    )
    .await;
}

#[tokio::test]
async fn health_checks_database() {
    let db = open_database(SqliteConnectOptions::new().in_memory(true))
        .await
        .unwrap();
    let app = app(db.clone());
    assert_eq!(
        request(&app, Method::GET, "/health", None, StatusCode::OK).await,
        json!({"status": "ok"})
    );
    db.close().await;
    request(
        &app,
        Method::GET,
        "/health",
        None,
        StatusCode::SERVICE_UNAVAILABLE,
    )
    .await;
}
