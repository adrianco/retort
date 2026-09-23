#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".into());
    let db = books_api::open_db(&db_path).expect("failed to open database");
    let listener = tokio::net::TcpListener::bind(&addr).await.expect("bind failed");
    println!("listening on {addr}");
    axum::serve(listener, books_api::app(db)).await.unwrap();
}
