use rusqlite::Connection;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let address = std::env::var("BIND_ADDRESS").unwrap_or_else(|_| "127.0.0.1:3000".into());
    let app = book_collection::app(Connection::open(path)?)?;
    let listener = tokio::net::TcpListener::bind(&address).await?;
    println!("Book API listening on {}", listener.local_addr()?);
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            if let Err(error) = tokio::signal::ctrl_c().await {
                eprintln!("signal error: {error}");
            }
        })
        .await?;
    Ok(())
}
