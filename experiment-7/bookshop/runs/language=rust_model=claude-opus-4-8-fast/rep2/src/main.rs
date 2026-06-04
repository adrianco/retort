use std::net::SocketAddr;

use book_collection::build_app;
use rusqlite::Connection;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = Connection::open(&db_path).expect("failed to open database");
    let app = build_app(conn).expect("failed to initialize database");

    let addr: SocketAddr = std::env::var("BIND_ADDR")
        .unwrap_or_else(|_| "127.0.0.1:3000".to_string())
        .parse()
        .expect("invalid BIND_ADDR");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind address");
    println!("Listening on http://{addr} (db: {db_path})");
    axum::serve(listener, app).await.expect("server error");
}
