use books_api::{build_app, init_db};
use tokio_rusqlite::Connection;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = Connection::open(&db_path).await?;
    init_db(&conn).await?;

    let app = build_app(conn).await;
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("Listening on {}", addr);
    axum::serve(listener, app).await?;
    Ok(())
}
