use book_collection::{app, open_db};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Database path is configurable; defaults to a local file.
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = open_db(&db_path)?;

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("Book collection API listening on http://{addr} (db: {db_path})");

    axum::serve(listener, app(db)).await?;
    Ok(())
}
