use book_collection_api::{app, db::Db};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = Db::open(&db_path).expect("failed to open database");

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    println!("Book collection API listening on http://{addr} (db: {db_path})");
    axum::serve(listener, app(db))
        .await
        .expect("server error");
}
