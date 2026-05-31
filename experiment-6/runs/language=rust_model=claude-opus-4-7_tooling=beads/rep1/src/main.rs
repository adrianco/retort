use books_api::{build_router, new_file_state};
use std::env;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt().init();

    let db_path = env::var("BOOKS_DB").unwrap_or_else(|_| "books.db".to_string());
    let addr = env::var("BOOKS_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());

    let state = new_file_state(&db_path);
    let app = build_router(state);

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("bind tcp listener");
    tracing::info!("books-api listening on {}", addr);
    axum::serve(listener, app).await.expect("axum serve");
}
