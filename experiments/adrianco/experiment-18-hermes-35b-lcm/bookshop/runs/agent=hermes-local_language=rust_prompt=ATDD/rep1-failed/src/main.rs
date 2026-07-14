
use book_api::init_database;
use std::env;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let db_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite:books.db".to_string());

    println!("Initializing database at: {}", db_url);

    let pool = init_database(&db_url).await;

    println!("Book API server running on http://0.0.0.0:8080");

    actix_web::HttpServer::new(move || {
        book_api::create_app(pool.clone())
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
