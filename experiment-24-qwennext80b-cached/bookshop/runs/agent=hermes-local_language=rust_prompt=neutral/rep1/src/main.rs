use actix_web::{web, App, HttpServer};
use book_api::{init_pool, health, get_books, get_book, create_book, update_book, delete_book};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize database
    let _ = init_pool().await;
    
    // Start the server
    let pool = init_pool().await;
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(health))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(get_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
