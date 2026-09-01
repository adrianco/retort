use book_api::{app, init_db};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let db = init_db(&db_path).expect("failed to open database");
    let addr = format!("0.0.0.0:{port}");
    let listener = tokio::net::TcpListener::bind(&addr).await.expect("bind failed");
    println!("book-api listening on http://{addr} (db: {db_path})");
    axum::serve(listener, app(db)).await.unwrap();
}
