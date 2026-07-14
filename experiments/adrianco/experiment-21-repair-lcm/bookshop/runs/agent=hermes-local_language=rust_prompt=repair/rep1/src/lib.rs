pub mod db;
pub mod models;
pub mod routes;
pub mod validation;

use std::sync::{Arc, Mutex};

use axum::{
    routing::{delete, get, post, put},
    Router,
};
use rusqlite::Connection;

pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
}

impl Clone for AppState {
    fn clone(&self) -> Self {
        AppState {
            db: Arc::clone(&self.db),
        }
    }
}

unsafe impl Send for AppState {}
unsafe impl Sync for AppState {}

pub fn create_router() -> Router<AppState> {
    let db_path = format!("test_{}.db", std::process::id());
    let conn = Connection::open(&db_path).expect("Failed to create test database");
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )
    .expect("Failed to create books table");

    Router::new()
        .route("/books", post(routes::create_book))
        .route("/books", get(routes::list_books))
        .route("/books/{id}", get(routes::get_book))
        .route("/books/{id}", put(routes::update_book))
        .route("/books/{id}", delete(routes::delete_book))
        .route("/health", get(routes::health_check))
        .with_state(AppState { db: Arc::new(Mutex::new(conn)) })
}
