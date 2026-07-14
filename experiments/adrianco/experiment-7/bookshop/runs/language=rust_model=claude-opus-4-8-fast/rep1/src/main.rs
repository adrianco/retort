use book_collection::{app, init_db};

#[tokio::main]
async fn main() {
    // Database path is configurable via DATABASE_PATH; defaults to a local file.
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = init_db(&db_path).expect("failed to initialise database");

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    println!("Book collection API listening on http://{addr}");
    axum::serve(listener, app(conn)).await.expect("server error");
}
