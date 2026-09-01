//! Book collection REST API built on axum + SQLite (rusqlite).

pub mod db;
pub mod handlers;
pub mod models;

use std::sync::{Arc, Mutex};

use axum::{
    routing::{get, post},
    Router,
};
use rusqlite::Connection;

/// Shared application state: a mutex-guarded SQLite connection.
#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
}

/// Build the application router around an already-initialised connection.
pub fn app(conn: Connection) -> Router {
    let state = AppState {
        db: Arc::new(Mutex::new(conn)),
    };
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
