use books_api::{app, open_db};

#[tokio::main]
async fn main() {
    let db = open_db("books.db");
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("listening on http://0.0.0.0:3000");
    axum::serve(listener, app(db)).await.unwrap();
}
