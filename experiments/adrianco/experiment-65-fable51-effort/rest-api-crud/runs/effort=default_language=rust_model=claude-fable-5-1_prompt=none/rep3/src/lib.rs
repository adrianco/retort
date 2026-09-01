//! Book collection REST API built on Axum and SQLite.
//!
//! The crate exposes [`app`] so the router can be driven directly in tests
//! without binding a socket, and [`Db`] for opening the backing store.

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use axum::{
    routing::{get, post},
    Router,
};

pub use db::Db;

/// Build the application router backed by `db`.
pub fn app(db: Db) -> Router {
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
        .with_state(db)
}
