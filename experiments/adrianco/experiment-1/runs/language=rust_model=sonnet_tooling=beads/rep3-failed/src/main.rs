mod db;
mod models;

use std::sync::{Arc, Mutex};

use axum::{
    Json, Router,
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use models::{Book, CreateBook, UpdateBook};

type Db = Arc<Mutex<Connection>>;

#[derive(Serialize)]
struct ErrorBody {
    error: String,
}

fn error(msg: impl Into<String>) -> (StatusCode, Json<ErrorBody>) {
    (StatusCode::BAD_REQUEST, Json(ErrorBody { error: msg.into() }))
}

fn internal(msg: impl std::fmt::Display) -> (StatusCode, Json<ErrorBody>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(ErrorBody { error: msg.to_string() }),
    )
}

// GET /health
async fn health() -> impl IntoResponse {
    Json(serde_json::json!({"status": "ok"}))
}

// POST /books
async fn create_book(
    State(db): State<Db>,
    Json(payload): Json<CreateBook>,
) -> impl IntoResponse {
    let title = match payload.title {
        Some(t) if !t.trim().is_empty() => t,
        _ => return error("title is required").into_response(),
    };
    let author = match payload.author {
        Some(a) if !a.trim().is_empty() => a,
        _ => return error("author is required").into_response(),
    };

    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        year: payload.year,
        isbn: payload.isbn,
    };

    let conn = db.lock().unwrap();
    if let Err(e) = db::insert_book(&conn, &book) {
        return internal(e).into_response();
    }

    (StatusCode::CREATED, Json(book)).into_response()
}

#[derive(Deserialize)]
struct AuthorQuery {
    author: Option<String>,
}

// GET /books
async fn list_books(
    State(db): State<Db>,
    Query(q): Query<AuthorQuery>,
) -> impl IntoResponse {
    let conn = db.lock().unwrap();
    match db::list_books(&conn, q.author.as_deref()) {
        Ok(books) => Json(books).into_response(),
        Err(e) => internal(e).into_response(),
    }
}

// GET /books/:id
async fn get_book(State(db): State<Db>, Path(id): Path<String>) -> impl IntoResponse {
    let conn = db.lock().unwrap();
    match db::get_book(&conn, &id) {
        Ok(Some(book)) => Json(book).into_response(),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(ErrorBody { error: "book not found".into() }),
        )
            .into_response(),
        Err(e) => internal(e).into_response(),
    }
}

// PUT /books/:id
async fn update_book(
    State(db): State<Db>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> impl IntoResponse {
    if payload.title.trim().is_empty() {
        return error("title is required").into_response();
    }
    if payload.author.trim().is_empty() {
        return error("author is required").into_response();
    }

    let conn = db.lock().unwrap();
    match db::update_book(&conn, &id, &payload) {
        Ok(true) => match db::get_book(&conn, &id) {
            Ok(Some(book)) => Json(book).into_response(),
            Ok(None) => (StatusCode::NOT_FOUND, Json(ErrorBody { error: "book not found".into() })).into_response(),
            Err(e) => internal(e).into_response(),
        },
        Ok(false) => (
            StatusCode::NOT_FOUND,
            Json(ErrorBody { error: "book not found".into() }),
        )
            .into_response(),
        Err(e) => internal(e).into_response(),
    }
}

// DELETE /books/:id
async fn delete_book(State(db): State<Db>, Path(id): Path<String>) -> impl IntoResponse {
    let conn = db.lock().unwrap();
    match db::delete_book(&conn, &id) {
        Ok(true) => StatusCode::NO_CONTENT.into_response(),
        Ok(false) => (
            StatusCode::NOT_FOUND,
            Json(ErrorBody { error: "book not found".into() }),
        )
            .into_response(),
        Err(e) => internal(e).into_response(),
    }
}

pub fn build_app(conn: Connection) -> Router {
    db::init_db(&conn).expect("failed to initialise DB");
    let db: Db = Arc::new(Mutex::new(conn));

    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(db)
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let conn = Connection::open("books.db").expect("failed to open database");
    let app = build_app(conn);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind");
    println!("Listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await.expect("server error");
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum_test::TestServer;

    fn test_server() -> TestServer {
        let conn = Connection::open_in_memory().unwrap();
        TestServer::new(build_app(conn)).unwrap()
    }

    #[tokio::test]
    async fn test_health() {
        let server = test_server();
        let resp = server.get("/health").await;
        resp.assert_status_ok();
        let val = resp.json::<serde_json::Value>();
        assert_eq!(val["status"], "ok");
    }

    #[tokio::test]
    async fn test_create_and_get_book() {
        let server = test_server();

        let payload = serde_json::json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2019
        });
        let create_resp = server.post("/books").json(&payload).await;
        create_resp.assert_status(StatusCode::CREATED);
        let book = create_resp.json::<serde_json::Value>();
        let id = book["id"].as_str().unwrap();
        assert_eq!(book["title"], "The Rust Programming Language");

        let get_resp = server.get(&format!("/books/{id}")).await;
        get_resp.assert_status_ok();
        let fetched = get_resp.json::<serde_json::Value>();
        assert_eq!(fetched["id"], id);
    }

    #[tokio::test]
    async fn test_validation_missing_title() {
        let server = test_server();
        let payload = serde_json::json!({ "author": "Someone" });
        let resp = server.post("/books").json(&payload).await;
        resp.assert_status(StatusCode::BAD_REQUEST);
        let val = resp.json::<serde_json::Value>();
        assert!(val["error"].as_str().unwrap().contains("title"));
    }

    #[tokio::test]
    async fn test_list_and_filter_books() {
        let server = test_server();

        for (title, author) in [("Book A", "Alice"), ("Book B", "Bob")] {
            server
                .post("/books")
                .json(&serde_json::json!({ "title": title, "author": author }))
                .await;
        }

        let all = server.get("/books").await.json::<serde_json::Value>();
        assert_eq!(all.as_array().unwrap().len(), 2);

        let filtered = server
            .get("/books")
            .add_query_param("author", "Alice")
            .await
            .json::<serde_json::Value>();
        assert_eq!(filtered.as_array().unwrap().len(), 1);
        assert_eq!(filtered[0]["author"], "Alice");
    }

    #[tokio::test]
    async fn test_update_and_delete_book() {
        let server = test_server();

        let create_resp = server
            .post("/books")
            .json(&serde_json::json!({ "title": "Old Title", "author": "Author" }))
            .await;
        create_resp.assert_status(StatusCode::CREATED);
        let book = create_resp.json::<serde_json::Value>();
        let id = book["id"].as_str().unwrap();

        let update_resp = server
            .put(&format!("/books/{id}"))
            .json(&serde_json::json!({ "title": "New Title", "author": "Author" }))
            .await;
        update_resp.assert_status_ok();
        let updated = update_resp.json::<serde_json::Value>();
        assert_eq!(updated["title"], "New Title");

        server
            .delete(&format!("/books/{id}"))
            .await
            .assert_status(StatusCode::NO_CONTENT);

        server
            .get(&format!("/books/{id}"))
            .await
            .assert_status(StatusCode::NOT_FOUND);
    }
}
