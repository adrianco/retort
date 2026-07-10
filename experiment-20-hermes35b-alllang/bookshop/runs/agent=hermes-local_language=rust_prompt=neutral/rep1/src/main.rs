use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    json::Json,
    routing::{delete, get, post, put},
    Router,
};
use rusqlite::{Connection, Result as SqliteResult};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use std::path::Path as StdPath;

mod db;
mod models;
mod routes;
mod validation;

use db::Database;
use models::*;
use routes::*;

#[derive(Clone)]
struct AppState {
    db: Mutex<Database>,
}

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = Database::new(&db_path).expect("Failed to initialize database");
    let state = AppState { db: Mutex::new(db) };

    let app = Router::new()
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book))
        .route("/books/{id}", put(update_book))
        .route("/books/{id}", delete(delete_book))
        .route("/health", get(health_check))
        .with_state(state);

    let addr = "0.0.0.0:3000";
    println!("Server running on http://{}", addr);
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .unwrap();
    axum::serve(listener, app).await.unwrap();
}
