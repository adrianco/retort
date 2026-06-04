use book_collection::{build_app, db};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());

    let pool = db::init_pool(&db_path);
    let app = build_app(pool);

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    println!("Book collection API listening on http://{addr}");
    axum::serve(listener, app)
        .await
        .expect("server error");
}
