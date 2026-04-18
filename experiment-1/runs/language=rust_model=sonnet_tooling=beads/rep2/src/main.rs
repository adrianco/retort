mod db;
mod handlers;
mod models;

use axum::{
    routing::get,
    Router,
};

pub fn create_app(pool: db::DbPool) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", get(handlers::list_books).post(handlers::create_book))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(pool)
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let db_path = std::env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string());
    let pool = db::init_db(&db_path).expect("Failed to initialize database");

    let app = create_app(pool);

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    tracing::info!("Listening on {}", addr);
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum_test::TestServer;
    use serde_json::{json, Value};

    fn test_server() -> TestServer {
        let pool = db::init_db(":memory:").expect("in-memory db");
        let app = create_app(pool);
        TestServer::new(app).unwrap()
    }

    #[tokio::test]
    async fn health_check_returns_ok() {
        let server = test_server();
        let resp = server.get("/health").await;
        resp.assert_status_ok();
        let body: Value = resp.json();
        assert_eq!(body["status"], "ok");
    }

    #[tokio::test]
    async fn create_and_get_book() {
        let server = test_server();

        // Create
        let resp = server
            .post("/books")
            .json(&json!({
                "title": "The Rust Programming Language",
                "author": "Steve Klabnik",
                "year": 2019,
                "isbn": "978-1-7185-0044-0"
            }))
            .await;
        resp.assert_status(axum::http::StatusCode::CREATED);
        let created: Value = resp.json();
        let id = created["id"].as_str().unwrap().to_string();
        assert_eq!(created["title"], "The Rust Programming Language");

        // Get by ID
        let resp = server.get(&format!("/books/{id}")).await;
        resp.assert_status_ok();
        let fetched: Value = resp.json();
        assert_eq!(fetched["id"], id);
        assert_eq!(fetched["author"], "Steve Klabnik");
    }

    #[tokio::test]
    async fn list_books_with_author_filter() {
        let server = test_server();

        // Add two books with different authors
        server
            .post("/books")
            .json(&json!({"title": "Book A", "author": "Alice"}))
            .await;
        server
            .post("/books")
            .json(&json!({"title": "Book B", "author": "Bob"}))
            .await;

        let resp = server.get("/books?author=Alice").await;
        resp.assert_status_ok();
        let books: Value = resp.json();
        let arr = books.as_array().unwrap();
        assert_eq!(arr.len(), 1);
        assert_eq!(arr[0]["author"], "Alice");
    }

    #[tokio::test]
    async fn validation_rejects_missing_title() {
        let server = test_server();
        let resp = server
            .post("/books")
            .json(&json!({"author": "Someone"}))
            .await;
        resp.assert_status(axum::http::StatusCode::UNPROCESSABLE_ENTITY);
        let body: Value = resp.json();
        assert!(body["error"].as_str().unwrap().contains("title"));
    }

    #[tokio::test]
    async fn update_and_delete_book() {
        let server = test_server();

        let resp = server
            .post("/books")
            .json(&json!({"title": "Old Title", "author": "Author"}))
            .await;
        let created: Value = resp.json();
        let id = created["id"].as_str().unwrap().to_string();

        // Update
        let resp = server
            .put(&format!("/books/{id}"))
            .json(&json!({"title": "New Title"}))
            .await;
        resp.assert_status_ok();
        let updated: Value = resp.json();
        assert_eq!(updated["title"], "New Title");
        assert_eq!(updated["author"], "Author"); // unchanged

        // Delete
        let resp = server.delete(&format!("/books/{id}")).await;
        resp.assert_status(axum::http::StatusCode::NO_CONTENT);

        // Confirm gone
        let resp = server.get(&format!("/books/{id}")).await;
        resp.assert_status(axum::http::StatusCode::NOT_FOUND);
    }
}
