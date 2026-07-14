mod db;
mod models;

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::{json, Value};
use std::sync::{Arc, Mutex};

use models::{CreateBook, ErrorResponse, UpdateBook};

type AppState = Arc<Mutex<Connection>>;

#[derive(Deserialize)]
struct AuthorFilter {
    author: Option<String>,
}

async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<CreateBook>,
) -> (StatusCode, Json<Value>) {
    let title = match &input.title {
        Some(t) if !t.trim().is_empty() => t.clone(),
        _ => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!(ErrorResponse { error: "title is required".into() })),
            )
        }
    };
    let author = match &input.author {
        Some(a) if !a.trim().is_empty() => a.clone(),
        _ => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!(ErrorResponse { error: "author is required".into() })),
            )
        }
    };

    let book = db::create_book_from_input(&models::CreateBook {
        title: Some(title),
        author: Some(author),
        year: input.year,
        isbn: input.isbn,
    });

    let conn = state.lock().unwrap();
    match db::insert_book(&conn, &book) {
        Ok(_) => (StatusCode::CREATED, Json(json!(book))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse { error: e.to_string() })),
        ),
    }
}

async fn list_books(
    State(state): State<AppState>,
    Query(filter): Query<AuthorFilter>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::list_books(&conn, filter.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(json!(books))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse { error: e.to_string() })),
        ),
    }
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::get_book(&conn, &id) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse { error: "book not found".into() })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse { error: e.to_string() })),
        ),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(input): Json<UpdateBook>,
) -> (StatusCode, Json<Value>) {
    // Validate that if title/author are provided they aren't empty strings
    if let Some(title) = &input.title {
        if title.trim().is_empty() {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!(ErrorResponse { error: "title cannot be empty".into() })),
            );
        }
    }
    if let Some(author) = &input.author {
        if author.trim().is_empty() {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!(ErrorResponse { error: "author cannot be empty".into() })),
            );
        }
    }

    let conn = state.lock().unwrap();
    match db::update_book(&conn, &id, &input) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse { error: "book not found".into() })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse { error: e.to_string() })),
        ),
    }
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let conn = state.lock().unwrap();
    match db::delete_book(&conn, &id) {
        Ok(true) => (StatusCode::NO_CONTENT, Json(json!(null))),
        Ok(false) => (
            StatusCode::NOT_FOUND,
            Json(json!(ErrorResponse { error: "book not found".into() })),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!(ErrorResponse { error: e.to_string() })),
        ),
    }
}

pub fn build_app(conn: Connection) -> Router {
    let state: AppState = Arc::new(Mutex::new(conn));
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(state)
}

#[tokio::main]
async fn main() {
    let conn = Connection::open("books.db").expect("Failed to open database");
    db::init_db(&conn).expect("Failed to initialize database");

    let app = build_app(conn);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("Listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum_test::TestServer;
    use serde_json::json;

    fn test_app() -> TestServer {
        let conn = Connection::open_in_memory().unwrap();
        db::init_db(&conn).unwrap();
        let app = build_app(conn);
        TestServer::new(app).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = test_app();
        let resp = server.get("/health").await;
        resp.assert_status_ok();
        let body: Value = resp.json();
        assert_eq!(body["status"], "ok");
    }

    #[tokio::test]
    async fn test_create_and_get_book() {
        let server = test_app();

        let resp = server
            .post("/books")
            .json(&json!({ "title": "Rust Programming", "author": "Steve Klabnik", "year": 2022 }))
            .await;
        resp.assert_status(StatusCode::CREATED);
        let book: Value = resp.json();
        assert_eq!(book["title"], "Rust Programming");
        assert_eq!(book["author"], "Steve Klabnik");

        let id = book["id"].as_str().unwrap();
        let get_resp = server.get(&format!("/books/{id}")).await;
        get_resp.assert_status_ok();
        let fetched: Value = get_resp.json();
        assert_eq!(fetched["id"], book["id"]);
    }

    #[tokio::test]
    async fn test_create_book_missing_required_fields() {
        let server = test_app();

        // Missing author
        let resp = server
            .post("/books")
            .json(&json!({ "title": "Only Title" }))
            .await;
        resp.assert_status(StatusCode::BAD_REQUEST);
        let body: Value = resp.json();
        assert!(body["error"].as_str().unwrap().contains("author"));
    }

    #[tokio::test]
    async fn test_list_books_with_author_filter() {
        let server = test_app();

        server.post("/books").json(&json!({ "title": "Book A", "author": "Alice" })).await;
        server.post("/books").json(&json!({ "title": "Book B", "author": "Bob" })).await;
        server.post("/books").json(&json!({ "title": "Book C", "author": "Alice" })).await;

        let resp = server.get("/books?author=Alice").await;
        resp.assert_status_ok();
        let books: Value = resp.json();
        let arr = books.as_array().unwrap();
        assert_eq!(arr.len(), 2);
        assert!(arr.iter().all(|b| b["author"] == "Alice"));
    }

    #[tokio::test]
    async fn test_update_book() {
        let server = test_app();

        let resp = server
            .post("/books")
            .json(&json!({ "title": "Old Title", "author": "Author" }))
            .await;
        let book: Value = resp.json();
        let id = book["id"].as_str().unwrap();

        let update_resp = server
            .put(&format!("/books/{id}"))
            .json(&json!({ "title": "New Title" }))
            .await;
        update_resp.assert_status_ok();
        let updated: Value = update_resp.json();
        assert_eq!(updated["title"], "New Title");
        assert_eq!(updated["author"], "Author");
    }

    #[tokio::test]
    async fn test_delete_book() {
        let server = test_app();

        let resp = server
            .post("/books")
            .json(&json!({ "title": "To Delete", "author": "Author" }))
            .await;
        let book: Value = resp.json();
        let id = book["id"].as_str().unwrap();

        let del_resp = server.delete(&format!("/books/{id}")).await;
        del_resp.assert_status(StatusCode::NO_CONTENT);

        let get_resp = server.get(&format!("/books/{id}")).await;
        get_resp.assert_status(StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_get_nonexistent_book() {
        let server = test_app();
        let resp = server.get("/books/nonexistent-id").await;
        resp.assert_status(StatusCode::NOT_FOUND);
    }
}
