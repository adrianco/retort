use books_api::{app, init_db};
use std::sync::{Arc, Mutex};

#[tokio::main]
async fn main() {
    let conn = init_db(":memory:").expect("failed to init db");
    let state = Arc::new(Mutex::new(conn));
    let app = app(state);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.unwrap();
}
