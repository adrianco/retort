use book_collection::{app, Database};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let address = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".into());
    let database = Database::open(path)?;
    let listener = tokio::net::TcpListener::bind(&address).await?;
    eprintln!("Listening on http://{}", listener.local_addr()?);
    axum::serve(listener, app(database))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
