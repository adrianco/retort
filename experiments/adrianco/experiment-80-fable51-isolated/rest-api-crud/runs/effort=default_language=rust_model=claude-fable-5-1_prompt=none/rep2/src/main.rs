use std::{env, error::Error};

use rusqlite::Connection;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let db_path = env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port = env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let host = env::var("HOST").unwrap_or_else(|_| "127.0.0.1".to_string());

    let app = books_api::app(Connection::open(&db_path)?)?;
    let listener = tokio::net::TcpListener::bind(format!("{host}:{port}")).await?;
    println!(
        "listening on http://{} (database: {db_path})",
        listener.local_addr()?
    );
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
