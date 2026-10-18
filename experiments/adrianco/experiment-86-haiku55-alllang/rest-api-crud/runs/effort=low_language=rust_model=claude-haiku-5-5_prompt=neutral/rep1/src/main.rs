use book_api::{app, AppState};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());

    let state = AppState::open(&db_path)?;
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("book_api listening on http://{addr} (database: {db_path})");
    axum::serve(listener, app(state)).await?;
    Ok(())
}
