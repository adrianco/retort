use book_collection_api::{app, AppState};

#[tokio::main]
async fn main() {
    let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_owned());
    let state = AppState::new(&database_url).expect("failed to initialize SQLite database");
    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000")
        .await
        .expect("failed to bind port 3000");
    println!("Book API listening on http://127.0.0.1:3000");
    axum::serve(listener, app(state))
        .await
        .expect("server error");
}
