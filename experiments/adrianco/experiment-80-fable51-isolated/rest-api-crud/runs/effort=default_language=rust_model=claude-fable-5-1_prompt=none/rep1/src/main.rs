use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port = env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let host = env::var("HOST").unwrap_or_else(|_| "127.0.0.1".to_string());

    let conn = books_api::open_db(&db_path)?;
    let listener = tokio::net::TcpListener::bind(format!("{host}:{port}")).await?;
    println!("listening on http://{}", listener.local_addr()?);

    axum::serve(listener, books_api::app(conn))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
