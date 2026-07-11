use axum::{
    routing::{delete, get, post, put},
    Router,
};
use std::sync::{Arc, Mutex};

mod db;
mod models;
mod routes;
mod validation;

use db::Database;

struct AppState {
    db: Arc<Mutex<Database>>,
}

impl Clone for AppState {
    fn clone(&self) -> Self {
        AppState {
            db: Arc::clone(&self.db),
        }
    }
}

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = Database::new(&db_path).expect("Failed to initialize database");
    let state = AppState {
        db: Arc::new(Mutex::new(db)),
    };

    let app = Router::new()
        .route("/books", post(routes::create_book))
        .route("/books", get(routes::list_books))
        .route("/books/{id}", get(routes::get_book))
        .route("/books/{id}", put(routes::update_book))
        .route("/books/{id}", delete(routes::delete_book))
        .route("/health", get(routes::health_check))
        .with_state(state);

    let addr = "0.0.0.0:3000";
    println!("Server running on http://{}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
