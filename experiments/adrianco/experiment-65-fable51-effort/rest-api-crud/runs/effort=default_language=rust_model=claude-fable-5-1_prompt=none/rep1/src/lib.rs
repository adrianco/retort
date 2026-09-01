//! Book collection REST API built on axum and SQLite.

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use axum::routing::get;
use axum::Router;

pub use db::Db;

/// Build the application router with the given database handle.
pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route(
            "/books",
            get(handlers::list_books).post(handlers::create_book),
        )
        .route(
            "/books/{id}",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(db)
}
