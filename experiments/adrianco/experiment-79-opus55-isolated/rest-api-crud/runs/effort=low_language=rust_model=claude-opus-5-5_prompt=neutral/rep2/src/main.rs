use books_api::{app, Db};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".into());
    let addr = format!("0.0.0.0:{port}");

    let db = Db::open(&db_path)?;
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("listening on http://{addr} (database: {db_path})");
    axum::serve(listener, app(db))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
