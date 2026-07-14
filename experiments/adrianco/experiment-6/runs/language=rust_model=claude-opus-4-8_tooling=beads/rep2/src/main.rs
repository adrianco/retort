use book_api::{app, init_pool};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_url =
        std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db?mode=rwc".to_string());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());

    let pool = init_pool(&db_url).await?;
    let app = app(pool);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("book-api listening on {addr} (db: {db_url})");
    axum::serve(listener, app).await?;
    Ok(())
}
