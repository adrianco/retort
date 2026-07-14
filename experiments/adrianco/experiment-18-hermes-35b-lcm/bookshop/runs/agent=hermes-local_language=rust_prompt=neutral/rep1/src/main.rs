use book_api::{create_pool, create_router};

#[tokio::main]
async fn main() {
    let pool = create_pool("books.db").await;
    let app = create_router(pool);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8000")
        .await
        .expect("failed to bind to port 8000");

    println!("Server running on http://0.0.0.0:8000");
    axum::serve(listener, app).await.expect("server error");
}
