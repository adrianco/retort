use books_api::{app, AppState};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());

    let state = AppState::open(&db_path)?;
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("listening on http://{} (database: {db_path})", listener.local_addr()?);
    axum::serve(listener, app(state))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
