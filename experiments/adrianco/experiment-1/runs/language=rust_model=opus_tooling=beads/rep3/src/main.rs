use books_api::{app, open_db};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    let db = open_db("books.db").expect("failed to open db");
    let app = app(db);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind");
    println!("listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await.expect("server error");
}
