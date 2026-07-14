use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use books_api::{app, open_memory_db, Book};
use serde_json::json;
use tower::ServiceExt;

async fn body_json(body: Body) -> serde_json::Value {
    let bytes = to_bytes(body, usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

fn req_json(method: &str, uri: &str, body: serde_json::Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

#[tokio::test]
async fn health_ok() {
    let db = open_memory_db().unwrap();
    let app = app(db);
    let res = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
}

#[tokio::test]
async fn create_and_get_book() {
    let db = open_memory_db().unwrap();
    let app = app(db);

    let res = app
        .clone()
        .oneshot(req_json(
            "POST",
            "/books",
            json!({"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"}),
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::CREATED);
    let created: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(created.title, "Dune");

    let res = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let fetched: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_missing_title_is_400() {
    let db = open_memory_db().unwrap();
    let app = app(db);
    let res = app
        .oneshot(req_json("POST", "/books", json!({"author": "X"})))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_filter_by_author_and_update_delete() {
    let db = open_memory_db().unwrap();
    let app = app(db);

    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        app.clone()
            .oneshot(req_json("POST", "/books", json!({"title": t, "author": a})))
            .await
            .unwrap();
    }

    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let list: Vec<Book> = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(list.len(), 2);
    assert!(list.iter().all(|b| b.author == "Alice"));

    let id = &list[0].id;

    let res = app
        .clone()
        .oneshot(req_json(
            "PUT",
            &format!("/books/{}", id),
            json!({"title": "Updated", "author": "Alice"}),
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let updated: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(updated.title, "Updated");

    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NO_CONTENT);

    let res = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}
