use std::env;

use books_api::{app, db};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let db_path = env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr = env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());

    let db = db::init(&db_path).expect("failed to initialize database");
    let app = app(db);

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind");
    tracing::info!("listening on {}", addr);
    axum::serve(listener, app).await.expect("server error");
}
