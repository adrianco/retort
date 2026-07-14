pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use axum::{
    routing::{get, post},
    Router,
};
use db::Pool;

/// Builds the application router wired up against the given connection pool.
pub fn app(pool: Pool) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(pool)
}
