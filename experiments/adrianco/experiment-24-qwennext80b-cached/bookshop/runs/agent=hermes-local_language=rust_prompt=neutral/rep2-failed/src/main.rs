mod database;
mod error;
mod handlers;
mod models;
mod tests;

use actix_web::{web, App, HttpServer};
use database::{init_db, DbPool};

#[actix_web::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database_url = "sqlite://data.db?mode=rwc";
    
    let pool = init_db(database_url).await?;
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(handlers::health))
            .route("/books", web::get().to(handlers::get_books))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books/{id}", web::get().to(handlers::get_book))
            .route("/books/{id}", web::put().to(handlers::update_book))
            .route("/books/{id}", web::delete().to(handlers::delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await?;

    Ok(())
}
