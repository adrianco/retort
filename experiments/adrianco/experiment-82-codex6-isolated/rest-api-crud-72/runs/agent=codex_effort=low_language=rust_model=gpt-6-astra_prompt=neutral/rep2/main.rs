use rusqlite::Connection;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let bind_address = std::env::var("BIND_ADDRESS").unwrap_or_else(|_| "127.0.0.1:3000".into());
    let app = book_collection::app(Connection::open(database_path)?)?;
    let listener = tokio::net::TcpListener::bind(&bind_address).await?;
    println!("Listening on http://{}", listener.local_addr()?);
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            if let Err(error) = tokio::signal::ctrl_c().await {
                eprintln!("Failed to listen for shutdown signal: {error}");
            }
        })
        .await?;
    Ok(())
}
