use book_api::{db, handlers, DbPool};
use actix_web::{web, App, HttpServer};
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let manager = SqliteConnectionManager::file("books.db");
    let pool: DbPool = Pool::new(manager).expect("Failed to create connection pool");

    db::init_db(&pool).expect("Failed to initialize database");

    println!("Starting server at http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(handlers::health_check))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books", web::get().to(handlers::list_books))
            .route("/books/{id}", web::get().to(handlers::get_book))
            .route("/books/{id}", web::put().to(handlers::update_book))
            .route("/books/{id}", web::delete().to(handlers::delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
