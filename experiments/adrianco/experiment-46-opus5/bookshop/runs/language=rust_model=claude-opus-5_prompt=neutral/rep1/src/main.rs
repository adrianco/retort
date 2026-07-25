use std::net::SocketAddr;

use book_api::{AppState, app};

/// Configuration comes from the environment so the binary needs no flags:
///   BOOKS_DB   path to the SQLite file (default `books.db`, `:memory:` works)
///   BIND_ADDR  socket to listen on (default `127.0.0.1:3000`)
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("BOOKS_DB").unwrap_or_else(|_| "books.db".to_string());
    let bind_addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());
    let addr: SocketAddr = bind_addr.parse()?;

    let state = if db_path == ":memory:" {
        AppState::in_memory()?
    } else {
        AppState::open(&db_path)?
    };

    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("book-api listening on http://{addr} (database: {db_path})");

    axum::serve(listener, app(state)).await?;
    Ok(())
}
