pub mod db;
pub mod handlers;
pub mod models;

use axum::{
    routing::{get, post},
    Router,
};
use std::sync::Arc;

use crate::db::Db;

pub fn app(db: Arc<Db>) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(db)
}
