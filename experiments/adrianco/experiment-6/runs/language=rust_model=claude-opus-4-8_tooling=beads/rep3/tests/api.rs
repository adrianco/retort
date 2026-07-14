use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_collection_api::{app, db::Db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

fn test_app() -> axum::Router {
    let db = Db::open(":memory:").expect("open in-memory db");
    app(db)
}

async fn body_json(resp: axum::response::Response) -> Value {
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    if bytes.is_empty() {
        return Value::Null;
    }
    serde_json::from_slice(&bytes).unwrap()
}

fn post(uri: &str, payload: Value) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(payload.to_string()))
        .unwrap()
}

fn put(uri: &str, payload: Value) -> Request<Body> {
    Request::builder()
        .method("PUT")
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(payload.to_string()))
        .unwrap()
}

fn get(uri: &str) -> Request<Body> {
    Request::builder().uri(uri).body(Body::empty()).unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let resp = app.oneshot(get("/health")).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_json(resp).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_and_get_book() {
    let app = test_app();

    let resp = app
        .clone()
        .oneshot(post(
            "/books",
            json!({"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "978-0441013593"}),
        ))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created = body_json(resp).await;
    assert_eq!(created["title"], "Dune");
    assert_eq!(created["author"], "Herbert");
    assert_eq!(created["year"], 1965);
    let id = created["id"].as_i64().unwrap();

    let resp = app.oneshot(get(&format!("/books/{id}"))).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched = body_json(resp).await;
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["title"], "Dune");
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = test_app();

    // Missing title
    let resp = app
        .clone()
        .oneshot(post("/books", json!({"author": "Someone"})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Blank author
    let resp = app
        .oneshot(post("/books", json!({"title": "X", "author": "   "})))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_filters_by_author() {
    let app = test_app();

    for payload in [
        json!({"title": "A", "author": "Alice"}),
        json!({"title": "B", "author": "Bob"}),
        json!({"title": "C", "author": "Alice"}),
    ] {
        let resp = app.clone().oneshot(post("/books", payload)).await.unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

    let resp = app.clone().oneshot(get("/books")).await.unwrap();
    let all = body_json(resp).await;
    assert_eq!(all.as_array().unwrap().len(), 3);

    let resp = app.oneshot(get("/books?author=Alice")).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let filtered = body_json(resp).await;
    let arr = filtered.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    assert!(arr.iter().all(|b| b["author"] == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = test_app();

    let resp = app
        .clone()
        .oneshot(post("/books", json!({"title": "Old", "author": "Auth"})))
        .await
        .unwrap();
    let id = body_json(resp).await["id"].as_i64().unwrap();

    // Update
    let resp = app
        .clone()
        .oneshot(put(
            &format!("/books/{id}"),
            json!({"title": "New", "author": "Auth", "year": 2020}),
        ))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated = body_json(resp).await;
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["year"], 2020);

    // Delete
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Now gone
    let resp = app.oneshot(get(&format!("/books/{id}"))).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let resp = app.oneshot(get("/books/9999")).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
