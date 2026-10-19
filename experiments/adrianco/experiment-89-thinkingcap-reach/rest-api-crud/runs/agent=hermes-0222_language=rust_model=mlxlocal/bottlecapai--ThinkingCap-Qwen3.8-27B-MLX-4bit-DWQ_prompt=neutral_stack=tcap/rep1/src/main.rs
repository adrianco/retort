use std::net::SocketAddr;

use book_api::{open_db, router, AppState};
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("BOOKS_DB").unwrap_or_else(|_| "books.db".to_string());
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8000);

    let conn = open_db(&db_path)?;
    let state = AppState {
        db: std::sync::Arc::new(std::sync::Mutex::new(conn)),
    };
    let app = router(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    println!("Book API listening on http://{addr} (db: {db_path})");
    let listener = TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}
