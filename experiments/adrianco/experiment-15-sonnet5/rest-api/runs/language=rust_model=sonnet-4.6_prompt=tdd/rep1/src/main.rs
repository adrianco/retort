mod db;
mod handlers;
mod models;

use axum::{
    routing::{delete, get, post, put},
    Router,
};
use rusqlite::Connection;
use std::sync::{Arc, Mutex};

pub fn build_app(conn: Connection) -> Router {
    let state = Arc::new(Mutex::new(conn));
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book))
        .route("/books", get(handlers::list_books))
        .route("/books/:id", get(handlers::get_book))
        .route("/books/:id", put(handlers::update_book))
        .route("/books/:id", delete(handlers::delete_book))
        .with_state(state)
}

#[tokio::main]
async fn main() {
    let conn = Connection::open_in_memory().expect("open db");
    db::init_db(&conn).expect("init db");

    let app = build_app(conn);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("Listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Method, Request, StatusCode},
    };
    use http_body_util::BodyExt;
    use serde_json::{json, Value};
    use tower::ServiceExt;

    fn test_app() -> Router {
        let conn = Connection::open_in_memory().expect("open db");
        db::init_db(&conn).expect("init db");
        build_app(conn)
    }

    async fn body_json(body: axum::body::Body) -> Value {
        let bytes = body.collect().await.unwrap().to_bytes();
        if bytes.is_empty() {
            return Value::Null;
        }
        serde_json::from_slice(&bytes).unwrap()
    }

    async fn get_req(app: Router, path: &str) -> (StatusCode, Value) {
        let req = Request::builder()
            .method(Method::GET)
            .uri(path)
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        let status = resp.status();
        let json = body_json(resp.into_body()).await;
        (status, json)
    }

    async fn post_req(app: Router, path: &str, payload: Value) -> (StatusCode, Value) {
        let body = serde_json::to_vec(&payload).unwrap();
        let req = Request::builder()
            .method(Method::POST)
            .uri(path)
            .header("content-type", "application/json")
            .body(Body::from(body))
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        let status = resp.status();
        let json = body_json(resp.into_body()).await;
        (status, json)
    }

    async fn put_req(app: Router, path: &str, payload: Value) -> (StatusCode, Value) {
        let body = serde_json::to_vec(&payload).unwrap();
        let req = Request::builder()
            .method(Method::PUT)
            .uri(path)
            .header("content-type", "application/json")
            .body(Body::from(body))
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        let status = resp.status();
        let json = body_json(resp.into_body()).await;
        (status, json)
    }

    async fn delete_req(app: Router, path: &str) -> (StatusCode, Value) {
        let req = Request::builder()
            .method(Method::DELETE)
            .uri(path)
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        let status = resp.status();
        let json = body_json(resp.into_body()).await;
        (status, json)
    }

    // Helper: create a book and return (app, id)
    // Since tower::ServiceExt::oneshot consumes the app, we need to recreate
    // the app per request. To share state across calls we build the app once
    // and use the underlying Arc<Mutex<Connection>> directly in tests
    // that need multiple requests.

    #[tokio::test]
    async fn test_health_check() {
        let (status, body) = get_req(test_app(), "/health").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["status"], "ok");
    }

    #[tokio::test]
    async fn test_create_book_success() {
        let (status, body) = post_req(
            test_app(),
            "/books",
            json!({"title": "Rust Programming", "author": "Steve Klabnik", "year": 2019}),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
        assert_eq!(body["title"], "Rust Programming");
        assert_eq!(body["author"], "Steve Klabnik");
        assert_eq!(body["year"], 2019);
        assert!(body["id"].is_string());
    }

    #[tokio::test]
    async fn test_create_book_missing_title() {
        let (status, body) =
            post_req(test_app(), "/books", json!({"author": "Someone"})).await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
        assert!(body["error"].as_str().unwrap().contains("title"));
    }

    #[tokio::test]
    async fn test_create_book_missing_author() {
        let (status, body) =
            post_req(test_app(), "/books", json!({"title": "Some Book"})).await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
        assert!(body["error"].as_str().unwrap().contains("author"));
    }

    #[tokio::test]
    async fn test_list_books_empty() {
        let (status, body) = get_req(test_app(), "/books").await;
        assert_eq!(status, StatusCode::OK);
        assert!(body.as_array().unwrap().is_empty());
    }

    #[tokio::test]
    async fn test_list_and_get_books() {
        // Multi-request tests share one app via Arc<Mutex<Connection>>
        let conn = Connection::open_in_memory().expect("open db");
        db::init_db(&conn).expect("init db");
        let state = Arc::new(Mutex::new(conn));
        let make_app = || {
            use axum::routing::{delete, get, post, put};
            Router::new()
                .route("/health", get(handlers::health))
                .route("/books", post(handlers::create_book))
                .route("/books", get(handlers::list_books))
                .route("/books/:id", get(handlers::get_book))
                .route("/books/:id", put(handlers::update_book))
                .route("/books/:id", delete(handlers::delete_book))
                .with_state(state.clone())
        };

        // Create two books
        let (s, b1) = post_req(
            make_app(),
            "/books",
            json!({"title": "Book A", "author": "Author One"}),
        )
        .await;
        assert_eq!(s, StatusCode::CREATED);
        let (s, _) = post_req(
            make_app(),
            "/books",
            json!({"title": "Book B", "author": "Author Two"}),
        )
        .await;
        assert_eq!(s, StatusCode::CREATED);

        // List all
        let (s, body) = get_req(make_app(), "/books").await;
        assert_eq!(s, StatusCode::OK);
        assert_eq!(body.as_array().unwrap().len(), 2);

        // Filter by author
        let (s, body) = get_req(make_app(), "/books?author=Author+One").await;
        assert_eq!(s, StatusCode::OK);
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 1);
        assert_eq!(arr[0]["author"], "Author One");

        // Get by id
        let id = b1["id"].as_str().unwrap();
        let (s, body) = get_req(make_app(), &format!("/books/{id}")).await;
        assert_eq!(s, StatusCode::OK);
        assert_eq!(body["id"], id);
        assert_eq!(body["title"], "Book A");
    }

    #[tokio::test]
    async fn test_get_book_not_found() {
        let (status, _) = get_req(test_app(), "/books/nonexistent-id").await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_update_and_delete_book() {
        let conn = Connection::open_in_memory().expect("open db");
        db::init_db(&conn).expect("init db");
        let state = Arc::new(Mutex::new(conn));
        let make_app = || {
            use axum::routing::{delete, get, post, put};
            Router::new()
                .route("/health", get(handlers::health))
                .route("/books", post(handlers::create_book))
                .route("/books", get(handlers::list_books))
                .route("/books/:id", get(handlers::get_book))
                .route("/books/:id", put(handlers::update_book))
                .route("/books/:id", delete(handlers::delete_book))
                .with_state(state.clone())
        };

        let (_, created) = post_req(
            make_app(),
            "/books",
            json!({"title": "Old Title", "author": "Old Author"}),
        )
        .await;
        let id = created["id"].as_str().unwrap();

        // Update
        let (s, body) = put_req(
            make_app(),
            &format!("/books/{id}"),
            json!({"title": "New Title"}),
        )
        .await;
        assert_eq!(s, StatusCode::OK);
        assert_eq!(body["title"], "New Title");
        assert_eq!(body["author"], "Old Author");

        // Delete
        let (s, _) = delete_req(make_app(), &format!("/books/{id}")).await;
        assert_eq!(s, StatusCode::OK);

        // Confirm gone
        let (s, _) = get_req(make_app(), &format!("/books/{id}")).await;
        assert_eq!(s, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_update_not_found() {
        let (s, _) = put_req(
            test_app(),
            "/books/nonexistent",
            json!({"title": "X"}),
        )
        .await;
        assert_eq!(s, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_delete_not_found() {
        let (s, _) = delete_req(test_app(), "/books/nonexistent").await;
        assert_eq!(s, StatusCode::NOT_FOUND);
    }
}
