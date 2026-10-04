use books_api::{app, db};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let port = match std::env::var("PORT") {
        Ok(p) => p
            .parse::<u16>()
            .map_err(|_| format!("invalid PORT value: {p}"))?,
        Err(_) => 3000,
    };

    let conn = db::open(&db_path)?;
    let listener = tokio::net::TcpListener::bind(("0.0.0.0", port)).await?;
    println!("listening on http://{}", listener.local_addr()?);

    axum::serve(listener, app(conn))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
