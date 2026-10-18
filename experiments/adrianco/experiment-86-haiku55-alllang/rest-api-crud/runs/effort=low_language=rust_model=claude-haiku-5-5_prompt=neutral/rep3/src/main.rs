use book_api::app;
use rusqlite::Connection;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("BOOKS_DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());

    let conn = Connection::open(&db_path).expect("failed to open SQLite database");
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}"))
        .await
        .expect("failed to bind port");

    println!("book-api listening on http://0.0.0.0:{port} (db: {db_path})");
    axum::serve(listener, app(conn)).await.expect("server error");
}
