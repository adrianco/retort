pub mod db;
pub mod handlers;
pub mod models;

use axum::{
    routing::{get, post},
    Router,
};
use std::sync::{Arc, Mutex};

pub type AppState = Arc<Mutex<rusqlite::Connection>>;

pub fn build_router(state: AppState) -> Router {
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

pub fn new_in_memory_state() -> AppState {
    let conn = rusqlite::Connection::open_in_memory().expect("open in-memory sqlite");
    db::init_schema(&conn).expect("init schema");
    Arc::new(Mutex::new(conn))
}

pub fn new_file_state(path: &str) -> AppState {
    let conn = rusqlite::Connection::open(path).expect("open sqlite file");
    db::init_schema(&conn).expect("init schema");
    Arc::new(Mutex::new(conn))
}
