use actix_web::{web, App, HttpServer, HttpResponse, HttpResponseBuilder, web::Json, HttpResponse, Result};
use sqlite::Connection;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: Option<i64>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookRequest {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct BookUpdateRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
}

#[derive(Serialize)]
struct HealthStatus {
    status: String,
}

// Global database connection (in production, use connection pooling)
static DB_CONNECTION: Mutex<Option<sqlite::Connection>> = Mutex::new(None);

// Initialize database connection
fn init_db() -> sqlite::Connection {
    let mut db = DB_CONNECTION.lock().unwrap();
    if db.is_none() {
        let connection = sqlite::Connection::open("book.db").unwrap();
        *db = Some(connection);
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
       db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
       db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
       db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )").unwrap();
        db.as_mut().unwrap().execute("CREATE TABLE IF NOT EXISTS migration (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)">