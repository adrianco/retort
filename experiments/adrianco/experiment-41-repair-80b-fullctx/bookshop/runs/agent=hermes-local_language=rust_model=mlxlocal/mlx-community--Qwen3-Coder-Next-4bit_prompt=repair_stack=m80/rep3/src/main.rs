use actix_web::{web, App, HttpServer};
use book_api::{BookRepository, AppError};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let database_url = "sqlite://data.db";
    
    let repo = BookRepository::new(database_url).await.map_err(|e| {
        std::io::Error::new(std::io::ErrorKind::Other, format!("Failed to initialize database: {}", e))
    })?;
    
    println!("Starting server on http://127.0.0.1:8080");
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(repo.clone()))
            .route("/health", web::get().to(book_api::health))
            .route("/books", web::post().to(book_api::create_book))
            .route("/books", web::get().to(book_api::get_books))
            .route("/books/{id}", web::get().to(book_api::get_book))
            .route("/books/{id}", web::put().to(book_api::update_book))
            .route("/books/{id}", web::delete().to(book_api::delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
