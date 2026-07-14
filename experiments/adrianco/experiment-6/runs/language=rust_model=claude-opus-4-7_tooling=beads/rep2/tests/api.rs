use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use books_api::models::Book;
use books_api::{app, db};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

fn build_app() -> axum::Router {
    let db = db::open_in_memory().expect("open in-memory db");
    app(db)
}

async fn body_json(body: axum::body::Body) -> Value {
    let bytes = body.collect().await.unwrap().to_bytes();
    if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    }
}

fn req(method: Method, uri: &str, payload: Option<Value>) -> Request<Body> {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match payload {
        Some(v) => {
            builder = builder.header("content-type", "application/json");
            Body::from(serde_json::to_vec(&v).unwrap())
        }
        None => Body::empty(),
    };
    builder.body(body).unwrap()
}

#[tokio::test]
async fn health_returns_ok() {
    let app = build_app();
    let res = app
        .oneshot(req(Method::GET, "/health", None))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body = body_json(res.into_body()).await;
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_and_get_book() {
    let app = build_app();

    let payload = json!({
        "title": "The Pragmatic Programmer",
        "author": "Andy Hunt",
        "year": 1999,
        "isbn": "978-0201616224"
    });
    let res = app
        .clone()
        .oneshot(req(Method::POST, "/books", Some(payload)))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::CREATED);
    let created: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(created.title, "The Pragmatic Programmer");
    assert_eq!(created.author, "Andy Hunt");
    assert_eq!(created.year, Some(1999));

    let res = app
        .clone()
        .oneshot(req(
            Method::GET,
            &format!("/books/{}", created.id),
            None,
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let fetched: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = build_app();

    let res = app
        .clone()
        .oneshot(req(
            Method::POST,
            "/books",
            Some(json!({ "author": "x" })),
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);

    let res = app
        .oneshot(req(
            Method::POST,
            "/books",
            Some(json!({ "title": "x" })),
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = build_app();

    for (title, author) in [
        ("Book A", "Alice"),
        ("Book B", "Bob"),
        ("Book C", "Alice"),
    ] {
        let res = app
            .clone()
            .oneshot(req(
                Method::POST,
                "/books",
                Some(json!({ "title": title, "author": author })),
            ))
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::CREATED);
    }

    let res = app
        .clone()
        .oneshot(req(Method::GET, "/books", None))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let all: Vec<Book> = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(all.len(), 3);

    let res = app
        .oneshot(req(Method::GET, "/books?author=Alice", None))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let alice: Vec<Book> = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(alice.len(), 2);
    assert!(alice.iter().all(|b| b.author == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = build_app();

    let res = app
        .clone()
        .oneshot(req(
            Method::POST,
            "/books",
            Some(json!({ "title": "Old", "author": "Author" })),
        ))
        .await
        .unwrap();
    let created: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();

    let res = app
        .clone()
        .oneshot(req(
            Method::PUT,
            &format!("/books/{}", created.id),
            Some(json!({ "title": "New" })),
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let updated: Book = serde_json::from_value(body_json(res.into_body()).await).unwrap();
    assert_eq!(updated.title, "New");
    assert_eq!(updated.author, "Author");

    let res = app
        .clone()
        .oneshot(req(
            Method::DELETE,
            &format!("/books/{}", created.id),
            None,
        ))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NO_CONTENT);

    let res = app
        .oneshot(req(Method::GET, &format!("/books/{}", created.id), None))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}
