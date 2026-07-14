use axum::{
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;

use crate::database::Database;
use crate::handlers::*;

mod models;
mod database;
mod handlers;

#[tokio::main]
async fn main() {
    // Initialize database
    let db = match Database::new("sqlite:books.db").await {
        Ok(database) => database,
        Err(e) => {
            eprintln!("Failed to connect to database: {}", e);
            std::process::exit(1);
        }
    };

    // Create the application
    let app = Router::new()
        // Health check
        .route("/health", get(health))
        // Books endpoints
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        // Add state to the app
        .with_state(db);

    // Start the server
    let addr = SocketAddr::from(([127, 0, 0, 1], 8080));
    println!("Server running on http://{}", addr);
    
    // Use the new server API for axum 0.7
    let listener = tokio::net::TcpListener::bind(addr).await.expect("Failed to bind address");
    axum::serve(listener, app).await.expect("Failed to start server");
}