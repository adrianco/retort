use book_api::{app, db};
use rusqlite::Connection;
use std::sync::{Arc, Mutex};

#[tokio::main]
async fn main() {
    let conn = Connection::open("books.db").expect("failed to open database");
    db::init_db(&conn);

    let router = app(Arc::new(Mutex::new(conn)));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind to port 3000");

    println!("listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, router).await.expect("server error");
}
