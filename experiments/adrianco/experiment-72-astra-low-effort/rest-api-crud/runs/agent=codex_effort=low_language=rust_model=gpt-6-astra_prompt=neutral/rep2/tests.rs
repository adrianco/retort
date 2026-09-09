use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
    Router,
};
use book_collection::{app, Database};
use serde_json::{json, Value};
use tower::ServiceExt;

fn fresh() -> Router {
    app(Database::from_connection(rusqlite::Connection::open_in_memory().unwrap()).unwrap())
}
async fn request(
    app: &Router,
    method: &str,
    path: &str,
    body: Option<Value>,
) -> (StatusCode, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.map(|v| v.to_string()).unwrap_or_default()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    if status != StatusCode::NO_CONTENT {
        assert_eq!(response.headers()["content-type"], "application/json");
    }
    let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    (
        status,
        if bytes.is_empty() {
            Value::Null
        } else {
            serde_json::from_slice(&bytes).unwrap()
        },
    )
}
fn book() -> Value {
    json!({"title":"Dune", "author":"Frank Herbert", "year":1965, "isbn":"9780441172719"})
}

#[tokio::test]
async fn full_crud_lifecycle() {
    let app = fresh();
    assert_eq!(
        request(&app, "GET", "/books", None).await,
        (StatusCode::OK, json!([]))
    );
    let (status, created) = request(&app, "POST", "/books", Some(book())).await;
    assert_eq!(status, StatusCode::CREATED);
    let path = format!("/books/{}", created["id"]);
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["year"], 1965);
    assert_eq!(created["isbn"], "9780441172719");
    assert_eq!(
        request(&app, "GET", &path, None).await,
        (StatusCode::OK, created.clone())
    );
    assert_eq!(
        request(&app, "GET", "/books", None).await.1,
        json!([created])
    );
    let (status, updated) = request(
        &app,
        "PUT",
        &path,
        Some(json!({"title":" Dune Messiah ","author":" Frank Herbert "})),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["author"], "Frank Herbert");
    assert_eq!(updated["year"], Value::Null);
    assert_eq!(updated["isbn"], Value::Null);
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
async fn filters_by_exact_author_and_handles_sql_characters() {
    let app = fresh();
    request(&app, "POST", "/books", Some(book())).await;
    request(
        &app,
        "POST",
        "/books",
        Some(json!({"title":"Other","author":"O'Brien"})),
    )
    .await;
    let (status, books) = request(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Dune");
    assert_eq!(
        request(&app, "GET", "/books?author=O%27Brien", None)
            .await
            .1
            .as_array()
            .unwrap()
            .len(),
        1
    );
    for author in ["frank%20herbert", "missing", "%27%20OR%201%3D1--"] {
        assert_eq!(
            request(&app, "GET", &format!("/books?author={author}"), None)
                .await
                .1,
            json!([])
        );
    }
}

#[tokio::test]
async fn validates_create_and_update_without_changing_data() {
    let app = fresh();
    request(&app, "POST", "/books", Some(book())).await;
    for invalid in [
        json!({}),
        json!({"title":"Title"}),
        json!({"author":"Author"}),
        json!({"title":" ","author":"a"}),
        json!({"title":"t","author":"\t\n"}),
        json!({"title":"t","author":"a","year":"bad"}),
        json!({"title":null,"author":"a"}),
    ] {
        for (method, path) in [("POST", "/books"), ("PUT", "/books/1")] {
            let (status, error) = request(&app, method, path, Some(invalid.clone())).await;
            assert!(status.is_client_error());
            assert!(error["error"].is_string());
        }
    }
    let books = request(&app, "GET", "/books", None).await.1;
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Dune");
}

#[tokio::test]
async fn missing_books_and_bad_ids_have_json_errors() {
    let app = fresh();
    for method in ["GET", "PUT", "DELETE"] {
        assert_eq!(
            request(&app, method, "/books/999", Some(book())).await.0,
            StatusCode::NOT_FOUND
        );
        for id in ["abc", "0", "-1", "9999999999999999999999"] {
            assert_eq!(
                request(&app, method, &format!("/books/{id}"), Some(book()))
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
async fn malformed_json_and_media_type_errors_are_json() {
    for (content_type, body, expected) in [
        ("application/json", "{", StatusCode::BAD_REQUEST),
        ("text/plain", "{}", StatusCode::UNSUPPORTED_MEDIA_TYPE),
    ] {
        let response = fresh()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", content_type)
                    .body(Body::from(body))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), expected);
        assert_eq!(response.headers()["content-type"], "application/json");
        let value: Value =
            serde_json::from_slice(&to_bytes(response.into_body(), usize::MAX).await.unwrap())
                .unwrap();
        assert!(value["error"].is_string());
    }
}

#[tokio::test]
async fn health_and_creation_location() {
    let app = fresh();
    assert_eq!(
        request(&app, "GET", "/health", None).await,
        (StatusCode::OK, json!({"status":"ok"}))
    );
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(book().to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    assert_eq!(response.headers()["location"], "/books/1");
}

#[tokio::test]
async fn sqlite_persists_across_reopening() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("books.db");
    {
        let app = app(Database::open(&path).unwrap());
        assert_eq!(
            request(&app, "POST", "/books", Some(book())).await.0,
            StatusCode::CREATED
        );
    }
    let reopened = app(Database::open(&path).unwrap());
    assert_eq!(
        request(&reopened, "GET", "/books/1", None).await.1["title"],
        "Dune"
    );
}
