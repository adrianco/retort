//! Book collection REST API built on Axum with a SQLite backing store.

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use std::sync::{Arc, Mutex};

use axum::{
    routing::{get, post},
    Router,
};
use rusqlite::Connection;

/// Shared application state: a single SQLite connection behind a mutex.
#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
}

impl AppState {
    pub fn new(conn: Connection) -> Self {
        Self {
            db: Arc::new(Mutex::new(conn)),
        }
    }
}

/// Build the application router with all routes wired to the given state.
pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route(
            "/books",
            post(handlers::create_book).get(handlers::list_books),
        )
        .route(
            "/books/{id}",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
