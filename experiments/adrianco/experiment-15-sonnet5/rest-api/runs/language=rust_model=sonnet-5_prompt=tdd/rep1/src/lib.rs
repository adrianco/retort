pub mod db;
pub mod handlers;
pub mod models;

use axum::routing::get;
use axum::Router;
use rusqlite::Connection;
use std::sync::{Arc, Mutex};

pub type SharedConn = Arc<Mutex<Connection>>;

pub fn app(conn: SharedConn) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route(
            "/books",
            get(handlers::list_books).post(handlers::create_book),
        )
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(conn)
}

pub mod test_support {
    use super::*;

    pub fn test_app() -> Router {
        let conn = Connection::open_in_memory().expect("failed to open in-memory db");
        db::init_db(&conn);
        app(Arc::new(Mutex::new(conn)))
    }
}
