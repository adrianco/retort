use std::env;

use rusqlite::Connection;

#[tokio::main]
async fn main() {
    let db_path = env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port = env::var("PORT").unwrap_or_else(|_| "3000".to_string());

    let conn = Connection::open(&db_path).expect("failed to open database");
    let router = book_api::app(conn).expect("failed to initialise database schema");

    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}"))
        .await
        .expect("failed to bind port");
    println!("listening on http://localhost:{port} (database: {db_path})");
    axum::serve(listener, router).await.expect("server error");
}
