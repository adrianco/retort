use books_api::{app, Db};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".into());
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".into());
    let db = Db::open(&db_path)?;
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await?;
    println!("listening on http://{}", listener.local_addr()?);
    axum::serve(listener, app(db)).await?;
    Ok(())
}
