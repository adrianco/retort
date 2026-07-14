use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use books_api::{app, open_memory_db, Book};
use serde_json::{json, Value};
use tower::ServiceExt;

async fn body_json(body: Body) -> Value {
    let bytes = to_bytes(body, usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_ok() {
    let router = app(open_memory_db());
    let resp = router
        .oneshot(Request::get("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let v = body_json(resp.into_body()).await;
    assert_eq!(v["status"], "ok");
}

#[tokio::test]
async fn create_get_update_delete_book() {
    let router = app(open_memory_db());

    // create
    let resp = router
        .clone()
        .oneshot(
            Request::post("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"})
                        .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created: Book = serde_json::from_value(body_json(resp.into_body()).await).unwrap();
    assert_eq!(created.title, "Dune");

    // get
    let resp = router
        .clone()
        .oneshot(
            Request::get(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let got: Book = serde_json::from_value(body_json(resp.into_body()).await).unwrap();
    assert_eq!(got.id, created.id);

    // update
    let resp = router
        .clone()
        .oneshot(
            Request::put(format!("/books/{}", created.id))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"title": "Dune Messiah", "author": "Herbert"}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: Book = serde_json::from_value(body_json(resp.into_body()).await).unwrap();
    assert_eq!(updated.title, "Dune Messiah");

    // delete
    let resp = router
        .clone()
        .oneshot(
            Request::delete(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // get -> 404
    let resp = router
        .oneshot(
            Request::get(format!("/books/{}", created.id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_requires_title_and_author() {
    let router = app(open_memory_db());
    let resp = router
        .oneshot(
            Request::post("/books")
                .header("content-type", "application/json")
                .body(Body::from(json!({"title": "x"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_and_filter_by_author() {
    let router = app(open_memory_db());

    for (t, a) in [("A", "Alice"), ("B", "Bob"), ("C", "Alice")] {
        router
            .clone()
            .oneshot(
                Request::post("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        json!({"title": t, "author": a}).to_string(),
                    ))
                    .unwrap(),
            )
            .await
            .unwrap();
    }

    let resp = router
        .clone()
        .oneshot(Request::get("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let all: Vec<Book> = serde_json::from_value(body_json(resp.into_body()).await).unwrap();
    assert_eq!(all.len(), 3);

    let resp = router
        .oneshot(
            Request::get("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let filtered: Vec<Book> = serde_json::from_value(body_json(resp.into_body()).await).unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b.author == "Alice"));
}
