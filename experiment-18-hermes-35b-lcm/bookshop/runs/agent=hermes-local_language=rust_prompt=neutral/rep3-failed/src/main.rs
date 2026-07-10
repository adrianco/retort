use actix_cors::Cors;
use actix_web::web;
use book_api::db::Database;
use book_api::routes;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let database = Database::new("books.db")
        .expect("Failed to initialize database");
    let database = web::Data::new(database);

    println!("Starting server on http://0.0.0.0:8080");

    actix_web::HttpServer::new(move || {
        let db = database.clone();
        let cors = Cors::default().allow_any_origin();
        actix_web::App::new()
            .app_data(db)
            .wrap(cors)
            .route("/health", web::get().to(routes::health_check))
            .route("/books", web::post().to(routes::create_book))
            .route("/books", web::get().to(routes::list_books))
            .route("/books/{id}", web::get().to(routes::get_book))
            .route("/books/{id}", web::put().to(routes::update_book))
            .route("/books/{id}", web::delete().to(routes::delete_book))
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
