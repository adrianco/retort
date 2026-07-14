use std::sync::Arc;

use book_api::{app, db::Db};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = Arc::new(Db::new(&db_path).expect("failed to open database"));
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind");
    println!("listening on {}", addr);
    axum::serve(listener, app(db)).await.expect("server error");
}
