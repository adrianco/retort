pub mod db;
pub mod error;
pub mod handlers;
pub mod models;
pub mod state;

pub use state::AppState;

use axum::Router;
use axum::routing::get;

/// Build the API router. Tests drive this directly with `tower::ServiceExt`,
/// so nothing here needs a listening socket.
pub fn app(state: AppState) -> Router {
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
        .fallback(handlers::not_found)
        .with_state(state)
}
