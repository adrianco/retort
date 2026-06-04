pub mod db;
pub mod handlers;
pub mod models;

use axum::{
    routing::{get, post},
    Router,
};

use crate::db::DbPool;
use crate::handlers::AppState;

/// Build the application router wired to the given database pool.
pub fn build_app(pool: DbPool) -> Router {
    let state = AppState { pool };

    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
