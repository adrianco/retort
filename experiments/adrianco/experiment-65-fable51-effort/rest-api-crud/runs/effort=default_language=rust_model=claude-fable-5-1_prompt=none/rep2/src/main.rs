use books_api::{app, db, AppState};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let bind = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());

    let conn = db::open(&db_path).unwrap_or_else(|e| {
        eprintln!("failed to open database {db_path}: {e}");
        std::process::exit(1);
    });

    let listener = tokio::net::TcpListener::bind(&bind)
        .await
        .unwrap_or_else(|e| {
            eprintln!("failed to bind {bind}: {e}");
            std::process::exit(1);
        });

    println!("books-api listening on http://{bind} (database: {db_path})");
    axum::serve(listener, app(AppState::new(conn)))
        .await
        .expect("server error");
}
