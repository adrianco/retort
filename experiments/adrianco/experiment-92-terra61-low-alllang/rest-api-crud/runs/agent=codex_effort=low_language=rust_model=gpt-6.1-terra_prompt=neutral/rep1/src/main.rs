use book_collection::{app, AppState};
use rusqlite::Connection;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let address = std::env::var("ADDRESS").unwrap_or_else(|_| "127.0.0.1:3000".into());
    let state = AppState::new(Connection::open(database)?)?;
    let listener = tokio::net::TcpListener::bind(&address).await?;
    println!("Listening on http://{address}");
    axum::serve(listener, app(state)).await?;
    Ok(())
}
