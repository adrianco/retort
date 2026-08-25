use actix_web::web;

use crate::handlers::{health_check, list_books, get_book, create_book, update_book, delete_book};

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/books")
            .route("", web::get().to(list_books))
            .route("", web::post().to(create_book))
            .route("/{id}", web::get().to(get_book))
            .route("/{id}", web::put().to(update_book))
            .route("/{id}", web::delete().to(delete_book)),
    );
    cfg.service(web::resource("/health").route(web::get().to(health_check)));
}
