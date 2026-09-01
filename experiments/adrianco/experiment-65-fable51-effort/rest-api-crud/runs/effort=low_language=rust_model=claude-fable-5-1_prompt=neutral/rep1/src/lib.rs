//! Book collection REST API built on Axum with SQLite storage.

pub mod db;
pub mod handlers;

use axum::{
    routing::{get, post},
    Router,
};
use std::sync::{Arc, Mutex};

/// Shared application state: a mutex-guarded SQLite connection.
pub type AppState = Arc<Mutex<rusqlite::Connection>>;

/// Build the application router backed by the given database connection.
pub fn app(conn: rusqlite::Connection) -> Router {
    let state: AppState = Arc::new(Mutex::new(conn));
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/{id}",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
