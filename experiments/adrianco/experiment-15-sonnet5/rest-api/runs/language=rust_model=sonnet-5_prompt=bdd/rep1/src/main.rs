use book_api::{app, db};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let db_path = std::env::var("BOOK_API_DB").unwrap_or_else(|_| "books.db".to_string());
    let pool = db::init_pool(&db_path);
    let router = app(pool);

    let addr = std::env::var("BOOK_API_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    tracing::info!("book_api listening on {addr}");
    axum::serve(listener, router)
        .await
        .expect("server error");
}
