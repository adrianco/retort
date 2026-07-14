use std::sync::{Arc, Mutex};

use book_api::{build_router, db};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = db::open(&db_path).expect("failed to open database");
    let shared_db = Arc::new(Mutex::new(conn));

    let app = build_router(shared_db);

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    tracing::info!("listening on {}", addr);
    axum::serve(listener, app).await.expect("server error");
}
