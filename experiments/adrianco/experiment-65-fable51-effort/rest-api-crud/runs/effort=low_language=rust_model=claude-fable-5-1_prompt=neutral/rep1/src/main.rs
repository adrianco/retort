use book_api::{app, db};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(3000);

    let conn = db::open(&db_path).expect("failed to open database");
    let listener = tokio::net::TcpListener::bind(("0.0.0.0", port))
        .await
        .expect("failed to bind");
    println!("book-api listening on http://0.0.0.0:{port} (db: {db_path})");
    axum::serve(listener, app(conn)).await.expect("server error");
}
