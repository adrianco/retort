use rusqlite::Connection;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = Connection::open(&db_path).expect("failed to open database");
    let app = books_api::app(conn);

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");
    println!("books-api listening on http://{addr} (db: {db_path})");
    axum::serve(listener, app).await.expect("server error");
}
