use axum::{body::Body, http::Request, Router};
use book_collection::{app, Database};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn service() -> Router {
    app(Database::open(":memory:").unwrap())
}
async fn request(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (u16, Value) {
    raw_request(
        app,
        method,
        uri,
        body.map(|v| v.to_string()).unwrap_or_default(),
    )
    .await
}
async fn raw_request(app: &Router, method: &str, uri: &str, body: String) -> (u16, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(uri)
                .header("content-type", "application/json")
                .body(Body::from(body))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.headers()["content-type"], "application/json");
    let status = response.status().as_u16();
    let data = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&data).unwrap())
}

#[tokio::test]
async fn crud_lifecycle() {
    let app = service();
    let original =
        json!({"title":"Dune", "author":"Frank Herbert", "year":1965, "isbn":"9780441172719"});
    let (status, book) = request(&app, "POST", "/books", Some(original.clone())).await;
    assert_eq!(status, 201);
    assert_eq!(book["id"], 1);
    for field in ["title", "author", "year", "isbn"] {
        assert_eq!(book[field], original[field]);
    }
    assert_eq!(request(&app, "GET", "/books/1", None).await, (200, book));
    let (status, updated) = request(
        &app,
        "PUT",
        "/books/1",
        Some(json!({"title":" Dune Messiah ", "author":" Frank Herbert ", "year":1969})),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(updated["title"], "Dune Messiah");
    assert_eq!(updated["author"], "Frank Herbert");
    assert_eq!(updated["year"], 1969);
    assert!(updated["isbn"].is_null());
    assert_eq!(request(&app, "GET", "/books/1", None).await, (200, updated));
    assert_eq!(
        request(&app, "DELETE", "/books/1", None).await,
        (200, json!({"deleted":1}))
    );
    assert_eq!(request(&app, "GET", "/books/1", None).await.0, 404);
    assert_eq!(request(&app, "GET", "/books", None).await, (200, json!([])));
}

#[tokio::test]
async fn author_filter_is_exact_and_parameterized() {
    let app = service();
    for author in ["Ursula Le Guin", "Octavia Butler", "Ursula Le Guin"] {
        assert_eq!(
            request(
                &app,
                "POST",
                "/books",
                Some(json!({"title":"A book", "author":author}))
            )
            .await
            .0,
            201
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
    let (status, books) = request(&app, "GET", "/books?author=Ursula%20Le%20Guin", None).await;
    assert_eq!(status, 200);
    assert_eq!(books.as_array().unwrap().len(), 2);
    assert_eq!(books[0]["id"], 1);
    assert_eq!(books[1]["id"], 3);
    for query in ["Nobody", "Ursula", "%27%20OR%201%3D1--"] {
        assert_eq!(
            request(&app, "GET", &format!("/books?author={query}"), None).await,
            (200, json!([]))
        );
    }
}

#[tokio::test]
async fn invalid_input_does_not_change_data() {
    let app = service();
    request(
        &app,
        "POST",
        "/books",
        Some(json!({"title":"Original", "author":"Writer"})),
    )
    .await;
    for body in [
        json!({}),
        json!({"title":"Title"}),
        json!({"author":"Author"}),
        json!({"title":" \t\n", "author":"Author"}),
        json!({"title":"Title", "author":""}),
        json!({"title":null, "author":"Author"}),
        json!({"title":"Title", "author":"Author", "year":"bad"}),
    ] {
        for (method, uri) in [("POST", "/books"), ("PUT", "/books/1")] {
            let (status, error) = request(&app, method, uri, Some(body.clone())).await;
            assert_eq!(status, 400);
            assert!(error["error"].is_string());
        }
    }
    assert_eq!(raw_request(&app, "POST", "/books", "{".into()).await.0, 400);
    let books = request(&app, "GET", "/books", None).await.1;
    assert_eq!(books.as_array().unwrap().len(), 1);
    assert_eq!(books[0]["title"], "Original");
}

#[tokio::test]
async fn health_missing_ids_and_routes() {
    let app = service();
    assert_eq!(
        request(&app, "GET", "/health", None).await,
        (200, json!({"status":"ok"}))
    );
    for method in ["GET", "PUT", "DELETE"] {
        let body = if method == "PUT" {
            Some(json!({"title":"Book", "author":"Author"}))
        } else {
            None
        };
        assert_eq!(
            request(&app, method, "/books/42", body.clone()).await.0,
            404
        );
        for id in ["abc", "0", "-1", "999999999999999999999999"] {
            assert_eq!(
                request(&app, method, &format!("/books/{id}"), body.clone())
                    .await
                    .0,
                400
            );
        }
    }
    assert_eq!(request(&app, "GET", "/missing", None).await.0, 404);
    assert_eq!(request(&app, "PATCH", "/books/1", None).await.0, 405);
}

#[tokio::test]
async fn books_persist_after_database_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("books.sqlite");
    {
        let app = app(Database::open(&path).unwrap());
        assert_eq!(
            request(
                &app,
                "POST",
                "/books",
                Some(json!({"title":"Persistent", "author":"Writer"}))
            )
            .await
            .0,
            201
        );
    }
    let app = app(Database::open(&path).unwrap());
    let (status, book) = request(&app, "GET", "/books/1", None).await;
    assert_eq!(status, 200);
    assert_eq!(book["title"], "Persistent");
}
