//! Entry point: opens the SQLite database and starts the axum HTTP server.

use std::sync::{Arc, Mutex};

use axum::Router;
use book_api::{init_db, router, AppState};
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8000);

    let conn = init_db(&db_path)?;
    let state = AppState {
        db: Arc::new(Mutex::new(conn)),
    };
    let app: Router = router(state);

    let listener = TcpListener::bind(("0.0.0.0", port)).await?;
    println!("Book API listening on http://localhost:{port} (database: {db_path})");
    axum::serve(listener, app).await?;
    Ok(())
}
